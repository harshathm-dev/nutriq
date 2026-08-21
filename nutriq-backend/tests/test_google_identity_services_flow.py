import pytest
import uuid
from unittest.mock import patch
import httpx
from httpx import AsyncClient, ASGITransport, Response
from app.main import app

def make_test_user():
    uid = uuid.uuid4().hex[:8]
    return {
        "name": f"Google User {uid}",
        "email": f"google_gis_user_{uid}@gmail.com",
        "google_id": f"google_sub_{uid}",
        "password": "SecurePassword123!"
    }

@pytest.mark.asyncio
async def test_google_identity_services_id_token_login_and_account_creation():
    """Test GIS ID token credential verification, new user creation, and session generation"""
    test_user = make_test_user()
    transport = ASGITransport(app=app)

    # Mock Google tokeninfo endpoint
    async def mock_get(self, url, *args, **kwargs):
        url_str = str(url)
        if "oauth2.googleapis.com/tokeninfo" in url_str:
            return Response(200, json={
                "email": test_user["email"],
                "name": test_user["name"],
                "sub": test_user["google_id"],
                "email_verified": "true"
            })
        return Response(404, json={"error": "not found"})

    with patch("httpx.AsyncClient.get", new=mock_get):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. New user logs in via Google Identity Services
            res1 = await client.post("/api/auth/google", json={
                "credential": "mock_valid_google_id_token_xyz"
            })
            assert res1.status_code == 200
            data1 = res1.json()
            assert data1["email"] == test_user["email"]
            assert data1["access_token"] is not None
            user_id = data1["user_id"]

            # 2. Second login with same Google account -> Returns same user account (idempotent, no duplicates)
            res2 = await client.post("/api/auth/google", json={
                "credential": "mock_valid_google_id_token_xyz"
            })
            assert res2.status_code == 200
            data2 = res2.json()
            assert data2["user_id"] == user_id
            assert data2["email"] == test_user["email"]


@pytest.mark.asyncio
async def test_google_identity_services_existing_email_linking():
    """Test that an existing email/password user logging in with Google gets linked seamlessly"""
    test_user = make_test_user()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register with email & password first
        reg_res = await client.post("/api/auth/register", json={
            "name": test_user["name"],
            "email": test_user["email"],
            "password": test_user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg_res.status_code == 201
        registered_user_id = reg_res.json()["user_id"]

        # 2. Later, user clicks 'Continue with Google' with same email
        async def mock_get(self, url, *args, **kwargs):
            return Response(200, json={
                "email": test_user["email"],
                "name": test_user["name"],
                "sub": test_user["google_id"],
                "email_verified": "true"
            })

        with patch("httpx.AsyncClient.get", new=mock_get):
            google_res = await client.post("/api/auth/google", json={
                "credential": "mock_token_for_linking"
            })
            assert google_res.status_code == 200
            google_data = google_res.json()
            # Must link to the exact same account
            assert google_data["user_id"] == registered_user_id
            assert google_data["email"] == test_user["email"]


@pytest.mark.asyncio
async def test_google_identity_services_oauth2_access_token_flow():
    """Test GIS OAuth2 access_token verification via userinfo endpoint"""
    test_user = make_test_user()
    transport = ASGITransport(app=app)

    async def mock_get(self, url, *args, **kwargs):
        url_str = str(url)
        if "googleapis.com/oauth2/v3/userinfo" in url_str:
            return Response(200, json={
                "email": test_user["email"],
                "name": test_user["name"],
                "sub": test_user["google_id"],
                "email_verified": True
            })
        return Response(400, json={"error": "invalid_token"})

    with patch("httpx.AsyncClient.get", new=mock_get):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/auth/google", json={
                "access_token": "ya29.mock_oauth2_access_token_123"
            })
            assert res.status_code == 200
            data = res.json()
            assert data["email"] == test_user["email"]
            assert data["access_token"] is not None


@pytest.mark.asyncio
async def test_google_identity_services_invalid_credential_error_handling():
    """Test that invalid Google credentials return 400 Bad Request with friendly detail"""
    transport = ASGITransport(app=app)

    async def mock_get(self, url, *args, **kwargs):
        return Response(400, json={"error": "invalid_token", "error_description": "Invalid Value"})

    with patch("httpx.AsyncClient.get", new=mock_get):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/auth/google", json={
                "credential": "invalid_or_expired_token"
            })
            assert res.status_code == 400
            err_data = res.json()
            assert "detail" in err_data
            assert "unsuccessful" in err_data["detail"].lower() or "invalid" in err_data["detail"].lower()
