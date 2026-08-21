import pytest
import uuid
import urllib.parse
from unittest.mock import patch, AsyncMock
import httpx
from httpx import AsyncClient, ASGITransport, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.config import settings
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.models.profile import UserProfile
from app.utils.security import verify_password


@pytest.mark.asyncio
async def test_google_oauth_initiate_url_generation():
    """
    Validates that GET /api/auth/google generates the official Google OAuth 2.0 authorization URL
    with prompt=select_account and appropriate scopes.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Case A: When GOOGLE_CLIENT_ID is set
        with patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com"):
            with patch.object(settings, "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback"):
                res = await client.get("/api/auth/google", follow_redirects=False)
                assert res.status_code == 302
                loc = res.headers.get("location")
                assert "accounts.google.com/o/oauth2/v2/auth" in loc
                assert "client_id=test-client-id.apps.googleusercontent.com" in loc
                assert "redirect_uri=" in loc
                assert "prompt=select_account" in loc
                assert "scope=" in loc
                assert "response_type=code" in loc

        # Case B: When GOOGLE_CLIENT_ID is not configured
        with patch.object(settings, "GOOGLE_CLIENT_ID", None):
            res = await client.get("/api/auth/google", follow_redirects=False)
            assert res.status_code == 302
            loc = res.headers.get("location")
            assert "error=unconfigured" in loc


@pytest.mark.asyncio
async def test_google_oauth_callback_cancellation_and_errors():
    """
    Validates that GET /api/auth/google/callback handles user cancellation and invalid codes gracefully.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. User cancels authentication on Google
        res_cancel = await client.get("/api/auth/google/callback?error=access_denied", follow_redirects=False)
        assert res_cancel.status_code == 302
        assert "error=google_cancelled" in res_cancel.headers.get("location")

        # 2. Missing code parameter
        res_missing = await client.get("/api/auth/google/callback", follow_redirects=False)
        assert res_missing.status_code == 302
        assert "error=google_failed" in res_missing.headers.get("location")


@pytest.mark.asyncio
async def test_google_oauth_callback_full_user_creation_and_linking():
    """
    Validates that a verified Google authorization code creates a new user or links to an existing user
    and redirects to the frontend with a valid NutriQ JWT session token.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        google_email = f"oauth_user_{uuid.uuid4().hex[:8]}@gmail.com"
        google_sub = f"sub_{uuid.uuid4().hex}"
        google_name = "Jane Google User"

        # Mock token response and userinfo from Google
        mock_token_resp = Response(
            status_code=200,
            json={"access_token": "mock_access_token", "id_token": "mock_id_token"}
        )
        mock_tokeninfo_resp = Response(
            status_code=200,
            json={
                "email": google_email,
                "name": google_name,
                "sub": google_sub,
                "aud": "test-google-client-id"
            }
        )

        orig_post = httpx.AsyncClient.post
        orig_get = httpx.AsyncClient.get

        async def custom_post(self, url, *args, **kwargs):
            if "oauth2.googleapis.com" in str(url):
                return mock_token_resp
            return await orig_post(self, url, *args, **kwargs)

        async def custom_get(self, url, *args, **kwargs):
            if "googleapis.com" in str(url):
                return mock_tokeninfo_resp
            return await orig_get(self, url, *args, **kwargs)

        with patch("httpx.AsyncClient.post", side_effect=custom_post, autospec=True):
            with patch("httpx.AsyncClient.get", side_effect=custom_get, autospec=True):
                with patch.object(settings, "GOOGLE_CLIENT_ID", "test-google-client-id"):
                    # 1. First-time Google Sign-In -> Create User
                    res = await client.get("/api/auth/google/callback?code=valid_auth_code_123", follow_redirects=False)
                    assert res.status_code == 302
                    loc = res.headers.get("location")
                    assert "/login?" in loc
                    parsed_url = urllib.parse.urlparse(loc)
                    query_params = urllib.parse.parse_qs(parsed_url.query)
                    assert "token" in query_params
                    assert query_params["email"][0] == google_email
                    user_id = query_params["user_id"][0]

                    # Verify user in database
                    async with AsyncSessionLocal() as session:
                        u_res = await session.execute(select(User).where(User.id == user_id))
                        user = u_res.scalar_one_or_none()
                        assert user is not None
                        assert user.email == google_email
                        assert user.google_id == google_sub
                        assert user.auth_provider == "google"

                    # 2. Subsequent Google Sign-In -> Links / Authenticates Existing User
                    res2 = await client.get("/api/auth/google/callback?code=valid_auth_code_456", follow_redirects=False)
                    assert res2.status_code == 302
                    loc2 = res2.headers.get("location")
                    query_params2 = urllib.parse.parse_qs(urllib.parse.urlparse(loc2).query)
                    assert query_params2["user_id"][0] == user_id


@pytest.mark.asyncio
async def test_email_password_login_and_registration_regression():
    """
    Confirms that standard email/password registration, login, and token generation remain 100% functional.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"pwd_user_{uuid.uuid4().hex[:8]}@example.com"
        pwd = "SecurePassword123!"

        # Register
        reg_res = await client.post("/api/auth/register", json={
            "email": email,
            "password": pwd,
            "name": "Password User",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg_res.status_code == 201
        reg_data = reg_res.json()
        assert reg_data["email"] == email
        assert "access_token" in reg_data

        # Login
        login_res = await client.post("/api/auth/login", json={
            "email": email,
            "password": pwd
        })
        assert login_res.status_code == 200
        login_data = login_res.json()
        assert login_data["user_id"] == reg_data["user_id"]
        assert "access_token" in login_data

        # Invalid password check
        bad_login = await client.post("/api/auth/login", json={
            "email": email,
            "password": "WrongPassword!"
        })
        assert bad_login.status_code == 401
