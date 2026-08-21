import pytest
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

from app.main import app
from app.config import settings
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.models.auth import PasswordResetToken
from app.services.email_service import EmailService
from sqlalchemy import select


@pytest.fixture
def unique_email():
    return f"authemail_{uuid.uuid4().hex[:8]}@example.com"


@pytest.mark.asyncio
async def test_welcome_email_on_registration(unique_email):
    """TEST: Creating a new account sends a welcome email with actual user name, no passwords/tokens."""
    transport = ASGITransport(app=app)
    
    with patch.object(EmailService, "send_welcome_email", return_value=True) as mock_welcome:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/auth/register", json={
                "name": "Jane Doe",
                "email": unique_email,
                "password": "Password123!",
                "terms_accepted": True,
                "ai_consent_accepted": True
            })
            assert res.status_code == 201
            data = res.json()
            assert "access_token" in data
            assert data["email"] == unique_email

        # Verify welcome email background dispatch
        mock_welcome.assert_called_once()
        call_args = mock_welcome.call_args[0]
        assert call_args[0] == unique_email
        assert call_args[1] == "Jane Doe"


@pytest.mark.asyncio
async def test_login_notification_email_on_valid_login(unique_email):
    """TEST: Successful email/password login triggers a login notification email with actual timestamp."""
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        reg_res = await client.post("/api/auth/register", json={
            "name": "Alex Smith",
            "email": unique_email,
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        token = reg_res.json()["access_token"]

        # Complete profile setup
        await client.post("/api/profile", headers={"Authorization": f"Bearer {token}"}, json={
            "name": "Alex Smith",
            "age": 28,
            "gender": "male",
            "height_cm": 178.0,
            "weight_kg": 74.0,
            "activity_level": "moderately_active",
            "fitness_goal": "maintain",
            "dietary_preference": "standard"
        })

        # Login with correct password
        with patch.object(EmailService, "send_login_notification", return_value=True) as mock_login_email:
            res = await client.post("/api/auth/login", json={
                "email": unique_email,
                "password": "Password123!"
            })
            assert res.status_code == 200
            assert "access_token" in res.json()

            # Verify login notification email was dispatched
            mock_login_email.assert_called_once()
            call_args = mock_login_email.call_args[0]
            assert call_args[0] == unique_email
            assert call_args[1] == "Alex Smith"
            assert isinstance(call_args[2], datetime)


@pytest.mark.asyncio
async def test_wrong_password_does_not_send_login_email(unique_email):
    """TEST: Failed login attempt does NOT trigger a login notification email."""
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        await client.post("/api/auth/register", json={
            "name": "Sarah Connor",
            "email": unique_email,
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })

        # Attempt login with wrong password
        with patch.object(EmailService, "send_login_notification", return_value=True) as mock_login_email:
            res = await client.post("/api/auth/login", json={
                "email": unique_email,
                "password": "WrongPassword999!"
            })
            assert res.status_code == 401
            # Email must NOT be sent
            mock_login_email.assert_not_called()


@pytest.mark.asyncio
async def test_google_login_email_behavior():
    """
    TEST:
    - First Google login -> Welcome email
    - Subsequent Google login -> Login notification email
    """
    transport = ASGITransport(app=app)
    google_email = f"google_user_{uuid.uuid4().hex[:8]}@gmail.com"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. First Google Login
        with patch.object(EmailService, "send_welcome_email", return_value=True) as mock_welcome, \
             patch.object(EmailService, "send_login_notification", return_value=True) as mock_login_email:
            
            res1 = await client.post("/api/auth/google", json={
                "email": google_email,
                "name": "Google Pioneer",
                "google_id": f"gid_{uuid.uuid4().hex[:8]}"
            })
            assert res1.status_code == 200
            mock_welcome.assert_called_once_with(google_email, "Google Pioneer")
            mock_login_email.assert_not_called()

        # 2. Subsequent Google Login
        with patch.object(EmailService, "send_welcome_email", return_value=True) as mock_welcome, \
             patch.object(EmailService, "send_login_notification", return_value=True) as mock_login_email:
            
            res2 = await client.post("/api/auth/google", json={
                "email": google_email,
                "name": "Google Pioneer",
                "google_id": f"gid_{uuid.uuid4().hex[:8]}"
            })
            assert res2.status_code == 200
            mock_welcome.assert_not_called()
            mock_login_email.assert_called_once()
            assert mock_login_email.call_args[0][0] == google_email


@pytest.mark.asyncio
async def test_forgot_password_user_enumeration_protection(unique_email):
    """
    TEST: User enumeration protection.
    Both registered and unregistered emails return identical generic success message.
    """
    transport = ASGITransport(app=app)
    unregistered_email = f"unregistered_{uuid.uuid4().hex[:8]}@example.com"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register a valid user
        await client.post("/api/auth/register", json={
            "name": "Registered User",
            "email": unique_email,
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })

        # 1. Request forgot password for registered user
        res_reg = await client.post("/api/auth/forgot-password", json={"email": unique_email})
        assert res_reg.status_code == 200
        data_reg = res_reg.json()

        # 2. Request forgot password for UNREGISTERED user
        res_unreg = await client.post("/api/auth/forgot-password", json={"email": unregistered_email})
        assert res_unreg.status_code == 200
        data_unreg = res_unreg.json()

        # Verify responses are 100% identical and generic
        assert data_reg["status"] == "success"
        assert data_unreg["status"] == "success"
        assert data_reg["message"] == data_unreg["message"]
        assert "If an account exists for this email address" in data_reg["message"]


@pytest.mark.asyncio
async def test_password_reset_end_to_end_flow(unique_email):
    """
    TEST: Complete password recovery flow:
    1. Request reset link
    2. Verify token hash in DB
    3. Validate token via API
    4. Submit new password
    5. Old password rejected on login
    6. New password accepted on login
    7. Reusing same token rejected
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        reg_res = await client.post("/api/auth/register", json={
            "name": "Reset Test User",
            "email": unique_email,
            "password": "OriginalPassword123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg_res.status_code == 201

        captured_token = None

        def capture_reset_email(to_email, user_name, raw_token):
            nonlocal captured_token
            captured_token = raw_token
            return True

        # 1. Request forgot password
        with patch.object(EmailService, "send_password_reset_email", side_effect=capture_reset_email):
            res = await client.post("/api/auth/forgot-password", json={"email": unique_email})
            assert res.status_code == 200

        assert captured_token is not None, "Password reset token was not generated."

        # 2. Check that the token stored in DB is hashed with SHA-256 (not raw token)
        computed_hash = hashlib.sha256(captured_token.encode("utf-8")).hexdigest()
        async with AsyncSessionLocal() as session:
            stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == computed_hash)
            token_record = (await session.execute(stmt)).scalar_one_or_none()
            assert token_record is not None
            assert token_record.token_hash != captured_token
            assert token_record.used_at is None
            
            exp = token_record.expires_at if token_record.expires_at.tzinfo else token_record.expires_at.replace(tzinfo=timezone.utc)
            assert exp > datetime.now(timezone.utc)

        # 3. Validate token via API
        val_res = await client.get(f"/api/auth/validate-reset-token?token={captured_token}")
        assert val_res.status_code == 200
        assert val_res.json()["valid"] is True

        # 4. Attempt reset with mismatched/short password (< 6 chars)
        bad_res = await client.post("/api/auth/reset-password", json={
            "token": captured_token,
            "new_password": "123"
        })
        assert bad_res.status_code in [400, 422]

        # 5. Reset password with valid new password
        new_password = "BrandNewSecurePassword456!"
        reset_res = await client.post("/api/auth/reset-password", json={
            "token": captured_token,
            "new_password": new_password
        })
        assert reset_res.status_code == 200
        assert "successfully updated" in reset_res.json()["message"]

        # 6. Verify old password fails login
        old_login = await client.post("/api/auth/login", json={
            "email": unique_email,
            "password": "OriginalPassword123!"
        })
        assert old_login.status_code == 401

        # 7. Verify new password succeeds login
        new_login = await client.post("/api/auth/login", json={
            "email": unique_email,
            "password": new_password
        })
        assert new_login.status_code == 200
        assert "access_token" in new_login.json()

        # 8. Verify token reuse is strictly prevented
        reuse_res = await client.post("/api/auth/reset-password", json={
            "token": captured_token,
            "new_password": "AnotherPassword789!"
        })
        assert reuse_res.status_code == 400
        assert "no longer valid" in reuse_res.json()["detail"]


@pytest.mark.asyncio
async def test_expired_reset_token_rejection(unique_email):
    """TEST: Expired reset tokens are rejected."""
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        await client.post("/api/auth/register", json={
            "name": "Expired Token User",
            "email": unique_email,
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })

        raw_token = f"expired_mock_token_{uuid.uuid4().hex}"
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        # Insert expired token record into DB (expired 1 hour ago)
        async with AsyncSessionLocal() as session:
            user_stmt = select(User).where(User.email == unique_email)
            user = (await session.execute(user_stmt)).scalars().first()
            assert user is not None
            
            expired_record = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
            )
            session.add(expired_record)
            await session.commit()

        # Validation check
        val_res = await client.get(f"/api/auth/validate-reset-token?token={raw_token}")
        assert val_res.status_code == 200
        assert val_res.json()["valid"] is False
        assert val_res.json()["reason"] == "expired"

        # Reset attempt check
        reset_res = await client.post("/api/auth/reset-password", json={
            "token": raw_token,
            "new_password": "NewPassword123!"
        })
        assert reset_res.status_code == 400
        assert "expired" in reset_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_email_delivery_failure_does_not_break_auth(unique_email):
    """TEST: If SMTP/email service fails, registration and login must still succeed."""
    transport = ASGITransport(app=app)

    # Force EmailService._send_email to return False (or raise internally handled)
    with patch.object(EmailService, "_send_email", return_value=False):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Registration succeeds
            reg_res = await client.post("/api/auth/register", json={
                "name": "Resilient User",
                "email": unique_email,
                "password": "Password123!",
                "terms_accepted": True,
                "ai_consent_accepted": True
            })
            assert reg_res.status_code == 201
            assert "access_token" in reg_res.json()

            # Login succeeds
            login_res = await client.post("/api/auth/login", json={
                "email": unique_email,
                "password": "Password123!"
            })
            assert login_res.status_code == 200
            assert "access_token" in login_res.json()
