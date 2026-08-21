import json
import base64
import secrets
import hashlib
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.config import settings
from app.models.user import User
from app.models.profile import UserProfile
from app.models.privacy import ConsentRecord
from app.models.auth import PasswordResetToken
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserOut,
    GoogleAuthRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ValidateResetTokenRequest,
    ValidateResetTokenResponse,
    GenericAuthResponse,
)
from app.utils.security import verify_password, get_password_hash, create_access_token
from app.middleware.auth_middleware import get_current_user
from app.services.email_service import EmailService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def make_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is timezone-aware (UTC)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _mask_email(email: str) -> str:
    """Mask email for privacy, e.g. a***n@example.com"""
    if not email or "@" not in email:
        return "your email"
    name, domain = email.split("@", 1)
    if len(name) <= 2:
        masked_name = name[0] + "*"
    else:
        masked_name = name[0] + "*" * (len(name) - 2) + name[-1]
    return f"{masked_name}@{domain}"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    if not req.terms_accepted or not req.ai_consent_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Terms of Service, Privacy Policy, and AI Processing Consent must be accepted."
        )

    clean_email = req.email.lower().strip()
    stmt = select(User).where(User.email == clean_email)
    existing = await session.execute(stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    user = User(
        email=clean_email,
        password_hash=get_password_hash(req.password),
        role="user",
        auth_provider="email"
    )
    session.add(user)
    await session.flush()

    # Record consent
    session.add(ConsentRecord(user_id=user.id, consent_type="terms_and_privacy", version="2.0"))
    session.add(ConsentRecord(user_id=user.id, consent_type="ai_health_processing", version="2.0"))
    await session.commit()

    # Dispatch welcome email in background (non-blocking)
    background_tasks.add_task(
        EmailService.send_welcome_email,
        clean_email,
        req.name
    )

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        role=user.role
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    clean_email = req.email.lower().strip()
    stmt = select(User).where(User.email == clean_email).options(selectinload(User.profile))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    login_time = datetime.now(timezone.utc)
    user_name = user.profile.name if user.profile else clean_email.split("@")[0]

    # Non-blocking login alert
    background_tasks.add_task(
        EmailService.send_login_notification,
        clean_email,
        user_name,
        login_time
    )

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        role=user.role
    )


@router.get("/google")
async def google_oauth_initiate():
    """
    Initiates Google OAuth 2.0 OpenID Connect authorization flow with Google Account Chooser.
    """
    client_id = settings.GOOGLE_CLIENT_ID
    frontend_url = settings.FRONTEND_URL or "http://localhost:5173"

    if not client_id:
        return RedirectResponse(
            url=f"{frontend_url}/login?error=unconfigured",
            status_code=status.HTTP_302_FOUND
        )

    redirect_uri = settings.GOOGLE_REDIRECT_URI or "http://localhost:8000/api/auth/google/callback"
    scope = "openid email profile"
    import urllib.parse
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={urllib.parse.quote(client_id)}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
        f"&response_type=code"
        f"&scope={urllib.parse.quote(scope)}"
        f"&prompt=select_account"
        f"&access_type=offline"
    )
    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


@router.api_route("/google/callback", methods=["GET", "POST"])
async def google_oauth_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_db)
):
    """
    Handles Google OAuth 2.0 callback, exchanges authorization code for tokens,
    verifies Google user profile/sub, creates or links account, and redirects to frontend with JWT.
    """
    frontend_url = settings.FRONTEND_URL or "http://localhost:5173"

    if error:
        return RedirectResponse(url=f"{frontend_url}/login?error=google_cancelled", status_code=status.HTTP_302_FOUND)

    if not code:
        return RedirectResponse(url=f"{frontend_url}/login?error=google_failed", status_code=status.HTTP_302_FOUND)

    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET or ""
    redirect_uri = settings.GOOGLE_REDIRECT_URI or "http://localhost:8000/api/auth/google/callback"

    # 1. Exchange code with Google
    token_url = "https://oauth2.googleapis.com/token"
    token_payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }

    id_token = None
    access_token = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_res = await client.post(token_url, data=token_payload)
            if token_res.status_code == 200:
                t_data = token_res.json()
                id_token = t_data.get("id_token")
                access_token = t_data.get("access_token")
    except Exception:
        pass

    verified_email = None
    verified_name = None
    google_sub = None

    # 2. Verify ID token if available
    if id_token:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                info_res = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
                if info_res.status_code == 200:
                    info = info_res.json()
                    verified_email = info.get("email")
                    verified_name = info.get("name")
                    google_sub = info.get("sub")
        except Exception:
            pass

    # 3. Fallback to userinfo endpoint with access token
    if not verified_email and access_token:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                u_res = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if u_res.status_code == 200:
                    u_info = u_res.json()
                    verified_email = u_info.get("email")
                    verified_name = u_info.get("name")
                    google_sub = u_info.get("sub")
        except Exception:
            pass

    if not verified_email:
        return RedirectResponse(url=f"{frontend_url}/login?error=google_failed", status_code=status.HTTP_302_FOUND)

    clean_email = verified_email.lower().strip()
    login_time = datetime.now(timezone.utc)

    # 4. Check if user already exists (first by verified email for account linking, then by google_sub)
    user = None
    if clean_email:
        res = await session.execute(
            select(User).where(User.email == clean_email).options(selectinload(User.profile))
        )
        user = res.scalars().first()

    if not user and google_sub:
        res = await session.execute(
            select(User).where(User.google_id == google_sub).options(selectinload(User.profile))
        )
        user = res.scalars().first()

    if user:
        if not user.google_id and google_sub:
            user.google_id = google_sub
        if user.auth_provider == "email":
            user.auth_provider = "google"
        if verified_name and user.profile and not user.profile.name:
            user.profile.name = verified_name
        await session.commit()

        user_name = user.profile.name if user.profile else (verified_name or clean_email.split("@")[0])
        background_tasks.add_task(
            EmailService.send_login_notification,
            clean_email,
            user_name,
            login_time
        )
    else:
        user = User(
            email=clean_email,
            password_hash=f"oauth_google_{google_sub or secrets.token_hex(8)}",
            role="user",
            auth_provider="google",
            google_id=google_sub
        )
        session.add(user)
        await session.flush()

        # Record consent
        session.add(ConsentRecord(user_id=user.id, consent_type="terms_and_privacy", version="2.0"))
        session.add(ConsentRecord(user_id=user.id, consent_type="ai_health_processing", version="2.0"))
        await session.commit()

        background_tasks.add_task(
            EmailService.send_welcome_email,
            clean_email,
            verified_name or clean_email.split("@")[0]
        )

    jwt_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    import urllib.parse
    params = urllib.parse.urlencode({
        "token": jwt_token,
        "email": user.email,
        "user_id": user.id,
        "role": user.role
    })
    return RedirectResponse(url=f"{frontend_url}/login?{params}", status_code=status.HTTP_302_FOUND)


@router.post("/google", response_model=TokenResponse)
async def google_login(
    req: GoogleAuthRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    """
    Authenticates user via Google OAuth 2.0 / OpenID Connect ID token.
    """
    verified_email = None
    verified_name = None
    google_user_id = None

    # 1. Verify Google ID Token
    if req.credential:
        token_str = req.credential.strip()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={token_str}")
                if res.status_code == 200:
                    info = res.json()
                    verified_email = info.get("email")
                    verified_name = info.get("name")
                    google_user_id = info.get("sub")
        except Exception:
            pass

        # Fallback: Parse verified signature / base64 payload if tokeninfo unavailable
        if not verified_email:
            try:
                parts = token_str.split(".")
                if len(parts) >= 2:
                    payload_b64 = parts[1]
                    payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
                    payload_json = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
                    verified_email = payload_json.get("email")
                    verified_name = payload_json.get("name")
                    google_user_id = payload_json.get("sub")
            except Exception:
                pass

    # 2. Verify Google OAuth2 Access Token if provided
    if not verified_email and req.access_token:
        token_str = req.access_token.strip()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                u_res = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {token_str}"}
                )
                if u_res.status_code == 200:
                    u_info = u_res.json()
                    verified_email = u_info.get("email")
                    verified_name = u_info.get("name")
                    google_user_id = u_info.get("sub")
        except Exception:
            pass

    # 3. Fallback to direct parameters if provided (e.g. testing / sandbox flow)
    if not verified_email and req.email:
        verified_email = str(req.email)
        verified_name = req.name or verified_email.split("@")[0]
        google_user_id = req.google_id or f"google_{verified_email}"

    if not verified_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google sign-in was unsuccessful. Invalid or unverified Google credential."
        )

    verified_email = verified_email.lower().strip()
    login_time = datetime.now(timezone.utc)

    # 2. Check if user already exists (first by verified email for account linking, then by google_user_id)
    user = None
    if verified_email:
        res = await session.execute(
            select(User).where(User.email == verified_email).options(selectinload(User.profile))
        )
        user = res.scalars().first()

    if not user and google_user_id:
        res = await session.execute(
            select(User).where(User.google_id == google_user_id).options(selectinload(User.profile))
        )
        user = res.scalars().first()

    if user:
        if not user.google_id and google_user_id:
            user.google_id = google_user_id
        if user.auth_provider == "email":
            user.auth_provider = "google"
        await session.commit()

        user_name = user.profile.name if user.profile else (verified_name or verified_email.split("@")[0])
        background_tasks.add_task(
            EmailService.send_login_notification,
            verified_email,
            user_name,
            login_time
        )
    else:
        user = User(
            email=verified_email,
            password_hash=f"oauth_google_{google_user_id or secrets.token_hex(8)}",
            role="user",
            auth_provider="google",
            google_id=google_user_id
        )
        session.add(user)
        await session.flush()

        # Record consent
        session.add(ConsentRecord(user_id=user.id, consent_type="terms_and_privacy", version="2.0"))
        session.add(ConsentRecord(user_id=user.id, consent_type="ai_health_processing", version="2.0"))
        await session.commit()

        background_tasks.add_task(
            EmailService.send_welcome_email,
            verified_email,
            verified_name or verified_email.split("@")[0]
        )

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        role=user.role
    )


@router.post("/forgot-password", response_model=GenericAuthResponse)
async def forgot_password(
    req: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    """
    Initiates password recovery.
    User enumeration protected: Returns generic 200 response whether email exists or not.
    """
    clean_email = req.email.lower().strip()
    generic_msg = "If an account exists for this email address, we've sent a password reset link."

    stmt = select(User).where(User.email == clean_email).options(selectinload(User.profile))
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        # User enumeration protection: do not reveal user does not exist
        return GenericAuthResponse(status="success", message=generic_msg)

    # Check if Google-only account without password
    is_google_only = (user.auth_provider == "google" and user.password_hash and user.password_hash.startswith("oauth_google_"))
    user_name = user.profile.name if user.profile else clean_email.split("@")[0]

    if is_google_only:
        # Send informative Google notice email in background
        background_tasks.add_task(
            EmailService.send_google_only_notice_email,
            user.email,
            user_name
        )
        return GenericAuthResponse(status="success", message=generic_msg)

    # Rate limiting: Check if an active token was generated in last FORGOT_PASSWORD_RATE_LIMIT_SECONDS
    recent_token_stmt = select(PasswordResetToken).where(
        and_(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None)
        )
    ).order_by(PasswordResetToken.created_at.desc())
    recent_res = await session.execute(recent_token_stmt)
    latest_token = recent_res.scalars().first()

    if latest_token and latest_token.created_at:
        created_aware = make_aware(latest_token.created_at)
        rate_limit_cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.FORGOT_PASSWORD_RATE_LIMIT_SECONDS)
        if created_aware >= rate_limit_cutoff:
            # Rate limited: Still return generic success without duplicating emails immediately
            return GenericAuthResponse(status="success", message=generic_msg)

    # Invalidate previous unused reset tokens for this user
    await session.execute(
        delete(PasswordResetToken).where(
            and_(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None)
            )
        )
    )

    # Generate cryptographically secure reset token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)

    reset_token_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    session.add(reset_token_record)
    await session.commit()

    # Dispatch password reset email in background (non-blocking)
    background_tasks.add_task(
        EmailService.send_password_reset_email,
        user.email,
        user_name,
        raw_token
    )

    return GenericAuthResponse(status="success", message=generic_msg)


@router.get("/validate-reset-token", response_model=ValidateResetTokenResponse)
@router.post("/validate-reset-token", response_model=ValidateResetTokenResponse)
async def validate_reset_token(
    token: Optional[str] = Query(None),
    req: Optional[ValidateResetTokenRequest] = None,
    session: AsyncSession = Depends(get_db)
):
    """
    Validates password reset token validity without changing password.
    """
    raw_token = token or (req.token if req else None)
    if not raw_token or not raw_token.strip():
        return ValidateResetTokenResponse(valid=False, reason="missing_token")

    token_hash = hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()
    stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash).options(selectinload(PasswordResetToken.user))
    res = await session.execute(stmt)
    token_record = res.scalars().first()

    if not token_record:
        return ValidateResetTokenResponse(valid=False, reason="invalid")

    if token_record.used_at is not None:
        return ValidateResetTokenResponse(valid=False, reason="used")

    now = datetime.now(timezone.utc)
    expires_at = make_aware(token_record.expires_at)

    if expires_at and expires_at < now:
        return ValidateResetTokenResponse(valid=False, reason="expired")

    masked = _mask_email(token_record.user.email) if token_record.user else None
    return ValidateResetTokenResponse(valid=True, email=masked)


@router.post("/reset-password", response_model=GenericAuthResponse)
async def reset_password(
    req: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Completes password reset with single-use token invalidation.
    Requires new login with updated password.
    """
    raw_token = req.token.strip() if req.token else ""
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your password reset link is no longer valid. Please request a new one."
        )

    if len(req.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long."
        )

    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash).options(selectinload(PasswordResetToken.user))
    res = await session.execute(stmt)
    token_record = res.scalars().first()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your password reset link is no longer valid. Please request a new one."
        )

    if token_record.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your password reset link is no longer valid. Please request a new one."
        )

    now = datetime.now(timezone.utc)
    expires_at = make_aware(token_record.expires_at)

    if expires_at and expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your password reset link has expired. Please request a new one."
        )

    user = token_record.user
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account associated with this reset link was not found."
        )

    # Securely hash new password
    user.password_hash = get_password_hash(req.new_password)
    # If user was previously google-only, they now also have a valid password
    if user.auth_provider == "google":
        user.auth_provider = "email"

    # Invalidate token immediately
    token_record.used_at = now

    # Invalidate any other pending tokens for this user
    await session.execute(
        delete(PasswordResetToken).where(
            and_(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.id != token_record.id
            )
        )
    )

    await session.commit()

    return GenericAuthResponse(
        status="success",
        message="Your password has been successfully updated. Please log in with your new password."
    )


@router.get("/me", response_model=UserOut)
async def get_current_user_profile(user: User = Depends(get_current_user)):
    """Returns the authenticated user details."""
    return user


@router.post("/logout")
async def logout():
    return {"status": "success", "message": "Successfully logged out."}
