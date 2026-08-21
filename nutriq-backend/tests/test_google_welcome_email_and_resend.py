import pytest
import uuid
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.main import app
from app.config import settings
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.models.meal import Meal, MealItem
from app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_scenario_1_new_google_account_receives_welcome_email():
    """
    TEST 1:
    When a user signs into NutriQ with Google for the FIRST TIME:
    - User account is created.
    - Welcome email is sent to user's Google email.
    - welcome_email_sent is updated to True in database.
    - User receives valid JWT token.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        test_email = f"new_google_user_{uuid.uuid4().hex[:8]}@gmail.com"
        test_name = "Alex Google"
        test_google_id = f"gsub_{uuid.uuid4().hex[:12]}"

        # Mock tokeninfo verification response
        mock_tokeninfo_resp = Response(
            status_code=200,
            json={
                "email": test_email,
                "name": test_name,
                "sub": test_google_id,
                "aud": "test-client-id"
            }
        )

        sent_emails = []

        def mock_send_welcome(to_email, user_name=None):
            sent_emails.append({"to": to_email, "name": user_name})
            return True

        with patch("httpx.AsyncClient.get", return_value=mock_tokeninfo_resp):
            with patch.object(EmailService, "send_welcome_email", side_effect=mock_send_welcome):
                res = await client.post("/api/auth/google", json={
                    "credential": "mock_id_token_jwt"
                })

                assert res.status_code == 200
                data = res.json()
                assert "access_token" in data
                user_id = data["user_id"]
                assert data["email"] == test_email

                # Background task executed welcome email
                assert len(sent_emails) == 1
                assert sent_emails[0]["to"] == test_email
                assert sent_emails[0]["name"] == test_name

                # Verify in Database that welcome_email_sent is True
                async with AsyncSessionLocal() as session:
                    user_db = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
                    assert user_db is not None
                    assert user_db.email == test_email
                    assert user_db.google_id == test_google_id
                    assert user_db.welcome_email_sent is True


@pytest.mark.asyncio
async def test_scenario_2_duplicate_google_login_no_repeated_email():
    """
    TEST 2:
    Same Google account logs in again:
    - Login succeeds normally.
    - NO new welcome email is sent.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        test_email = f"returning_google_{uuid.uuid4().hex[:8]}@gmail.com"
        test_name = "Sarah Returner"
        test_google_id = f"gsub_{uuid.uuid4().hex[:12]}"

        mock_tokeninfo_resp = Response(
            status_code=200,
            json={
                "email": test_email,
                "name": test_name,
                "sub": test_google_id
            }
        )

        welcome_email_count = 0

        def count_welcome(to_email, user_name=None):
            nonlocal welcome_email_count
            welcome_email_count += 1
            return True

        with patch("httpx.AsyncClient.get", return_value=mock_tokeninfo_resp):
            with patch.object(EmailService, "send_welcome_email", side_effect=count_welcome):
                # First Login (Registration)
                res1 = await client.post("/api/auth/google", json={"credential": "mock_jwt_1"})
                assert res1.status_code == 200
                assert welcome_email_count == 1

                # Second Login (Same account)
                res2 = await client.post("/api/auth/google", json={"credential": "mock_jwt_2"})
                assert res2.status_code == 200
                assert welcome_email_count == 1  # Still 1, NOT sent again!

                # Third Login (Page refresh / new session)
                res3 = await client.post("/api/auth/google", json={"credential": "mock_jwt_3"})
                assert res3.status_code == 200
                assert welcome_email_count == 1  # Still 1


@pytest.mark.asyncio
async def test_scenario_3_email_provider_failure_does_not_break_login():
    """
    TEST 3:
    Email provider temporarily fails (e.g. timeout, invalid key, rate limit):
    - Login MUST still succeed 100%.
    - Error is logged safely.
    - welcome_email_sent remains False so system can retry later.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        test_email = f"failure_test_user_{uuid.uuid4().hex[:8]}@gmail.com"
        test_name = "Bob Resilient"
        test_google_id = f"gsub_{uuid.uuid4().hex[:12]}"

        mock_tokeninfo_resp = Response(
            status_code=200,
            json={
                "email": test_email,
                "name": test_name,
                "sub": test_google_id
            }
        )

        # Simulate email provider throwing an exception or returning False
        def failing_send_welcome(to_email, user_name=None):
            return False

        with patch("httpx.AsyncClient.get", return_value=mock_tokeninfo_resp):
            with patch.object(EmailService, "send_welcome_email", side_effect=failing_send_welcome):
                res = await client.post("/api/auth/google", json={"credential": "mock_jwt_failing"})

                # Authentication must NEVER crash or return 500
                assert res.status_code == 200
                data = res.json()
                assert "access_token" in data
                user_id = data["user_id"]

                # Verify in DB: welcome_email_sent remains False
                async with AsyncSessionLocal() as session:
                    user_db = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
                    assert user_db is not None
                    assert user_db.welcome_email_sent is False


@pytest.mark.asyncio
async def test_scenario_4_account_linking_existing_email_user():
    """
    TEST 4:
    Existing email/password NutriQ user signs in using Google with the same verified email:
    - Account is linked to Google ID.
    - No duplicate user record is created.
    - If user already had welcome_email_sent = True, no duplicate welcome email is sent.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        shared_email = f"linked_user_{uuid.uuid4().hex[:8]}@gmail.com"
        password = "SecurePassword123!"
        test_google_id = f"gsub_link_{uuid.uuid4().hex[:8]}"

        # 1. User registers via email/password first
        res_reg = await client.post("/api/auth/register", json={
            "email": shared_email,
            "password": password,
            "name": "Original Email User",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert res_reg.status_code == 201
        original_user_id = res_reg.json()["user_id"]

        # Ensure welcome_email_sent is marked True on initial registration
        async with AsyncSessionLocal() as session:
            u = (await session.execute(select(User).where(User.id == original_user_id))).scalar_one_or_none()
            u.welcome_email_sent = True
            await session.commit()

        # 2. User signs in with Google using the same email
        mock_tokeninfo_resp = Response(
            status_code=200,
            json={
                "email": shared_email,
                "name": "Google Name",
                "sub": test_google_id
            }
        )

        welcome_calls = 0

        def track_welcome(to_email, user_name=None):
            nonlocal welcome_calls
            welcome_calls += 1
            return True

        with patch("httpx.AsyncClient.get", return_value=mock_tokeninfo_resp):
            with patch.object(EmailService, "send_welcome_email", side_effect=track_welcome):
                res_google = await client.post("/api/auth/google", json={"credential": "mock_google_jwt"})
                assert res_google.status_code == 200
                google_data = res_google.json()
                
                # Must use the SAME existing user_id
                assert google_data["user_id"] == original_user_id
                # No duplicate welcome email dispatched
                assert welcome_calls == 0

                # Verify Google ID linked on same user record
                async with AsyncSessionLocal() as session:
                    users_with_email = (await session.execute(select(User).where(User.email == shared_email))).scalars().all()
                    assert len(users_with_email) == 1
                    assert users_with_email[0].google_id == test_google_id


@pytest.mark.asyncio
async def test_scenario_5_user_data_isolation_new_google_user():
    """
    TEST 5:
    New Google user logs meals and queries summaries:
    - User's meals are strictly isolated to that user's ID.
    - No data leaks to or from other accounts.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create Google User A
        email_a = f"user_a_{uuid.uuid4().hex[:8]}@gmail.com"
        mock_resp_a = Response(status_code=200, json={"email": email_a, "name": "User A", "sub": f"sub_a_{uuid.uuid4().hex[:8]}"})
        with patch("httpx.AsyncClient.get", return_value=mock_resp_a):
            res_a = await client.post("/api/auth/google", json={"credential": "jwt_a"})
            token_a = res_a.json()["access_token"]
            user_a_id = res_a.json()["user_id"]

        # Create Google User B
        email_b = f"user_b_{uuid.uuid4().hex[:8]}@gmail.com"
        mock_resp_b = Response(status_code=200, json={"email": email_b, "name": "User B", "sub": f"sub_b_{uuid.uuid4().hex[:8]}"})
        with patch("httpx.AsyncClient.get", return_value=mock_resp_b):
            res_b = await client.post("/api/auth/google", json={"credential": "jwt_b"})
            token_b = res_b.json()["access_token"]
            user_b_id = res_b.json()["user_id"]

        # User A logs a meal: Dosa (300 kcal)
        res_meal_a = await client.post("/api/meals", headers={"Authorization": f"Bearer {token_a}"}, json={
            "meal_type": "breakfast",
            "date": "2026-08-21",
            "time": "08:30",
            "items": [{"name": "Plain Dosa", "calories": 300, "protein_g": 6, "carbs_g": 45, "fat_g": 8, "quantity": 1}]
        })
        assert res_meal_a.status_code == 201

        # User B queries their meals for that date -> MUST BE EMPTY
        res_history_b = await client.get("/api/meals/history?date=2026-08-21", headers={"Authorization": f"Bearer {token_b}"})
        assert res_history_b.status_code == 200
        data_b = res_history_b.json()
        assert len(data_b["meals"]) == 0
        assert data_b["total_calories"] == 0

        # User A queries their meals -> MUST HAVE 1 MEAL
        res_history_a = await client.get("/api/meals/history?date=2026-08-21", headers={"Authorization": f"Bearer {token_a}"})
        assert res_history_a.status_code == 200
        data_a = res_history_a.json()
        assert len(data_a["meals"]) == 1
        assert data_a["meals"][0]["items"][0]["name"] == "Plain Dosa"
        assert data_a["total_calories"] == 300


def test_resend_sdk_send_and_template_formatting():
    """
    TEST 6:
    Validates Resend SDK integration and welcome template content:
    - Subject: 'Welcome to NutriQ! 🌱'
    - Formatted HTML containing all requested feature bullet points.
    - Resend API call receives proper params.
    """
    with patch.object(settings, "RESEND_API_KEY", "re_test_key_12345"):
        with patch.object(settings, "WELCOME_EMAIL_FROM", "NutriQ <onboarding@resend.dev>"):
            mock_resend_response = {"id": "resend_msg_abc123"}
            
            with patch("resend.Emails.send", return_value=mock_resend_response) as mock_send:
                success = EmailService.send_welcome_email("alex@example.com", "Alex Hunter")
                assert success is True
                
                assert mock_send.called
                call_args = mock_send.call_args[0][0]
                assert call_args["to"] == ["alex@example.com"]
                assert call_args["from"] == "NutriQ <onboarding@resend.dev>"
                assert "Welcome to NutriQ" in call_args["subject"]
                
                # Check HTML and Plain text content
                html = call_args["html"]
                text = call_args["text"]
                assert "Alex Hunter" in html
                assert "Calories" in html
                assert "Protein" in html
                assert "Hydration" in html or "Water intake" in html
                assert "Alex Hunter" in text
                assert "The NutriQ Team" in text


@pytest.mark.asyncio
async def test_test_email_endpoint_success():
    """
    TEST 7:
    Tests POST /api/test-email with successful Resend dispatch.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch.object(settings, "RESEND_API_KEY", "re_mock_key_999"):
            with patch("resend.Emails.send", return_value={"id": "resend_test_id_555"}):
                res = await client.post("/api/test-email", json={"email": "tester@example.com"})
                assert res.status_code == 200
                data = res.json()
                assert data["status"] == "success"
                assert data["recipient"] == "tester@example.com"
                assert data["resend_id"] == "resend_test_id_555"
                assert data["provider"] == "resend"


@pytest.mark.asyncio
async def test_test_email_endpoint_resend_failure_diagnostic():
    """
    TEST 8:
    Tests POST /api/test-email when Resend returns an error (e.g. domain not verified).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch.object(settings, "RESEND_API_KEY", "re_mock_key_999"):
            with patch("resend.Emails.send", side_effect=Exception("The domain is not verified.")):
                res = await client.post("/api/test-email", json={"email": "tester@example.com"})
                assert res.status_code == 200
                data = res.json()
                assert data["status"] == "error"
                assert "domain is not verified" in data["error"]
                assert data["recipient"] == "tester@example.com"


@pytest.mark.asyncio
async def test_test_email_missing_api_key_error():
    """
    TEST 9:
    Tests POST /api/test-email when RESEND_API_KEY is not configured.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch.object(settings, "RESEND_API_KEY", None):
            with patch.object(settings, "EMAIL_PROVIDER", "resend"):
                res = await client.post("/api/test-email", json={"email": "tester@example.com"})
                assert res.status_code == 200
                data = res.json()
                assert data["status"] == "error"
                assert "RESEND_API_KEY is missing" in data["error"] or "not configured" in data["error"]

