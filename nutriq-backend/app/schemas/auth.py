from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    name: Optional[str] = None
    email: EmailStr
    password: str = Field(..., min_length=6)
    terms_accepted: bool = Field(default=True, description="Must be true to activate account")
    ai_consent_accepted: bool = Field(default=True, description="Consent for AI health processing")

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str

class UserOut(BaseModel):
    id: str
    email: str
    role: str
    auth_provider: Optional[str] = "email"
    welcome_email_sent: Optional[bool] = False
    created_at: datetime

    class Config:
        from_attributes = True


class GoogleAuthRequest(BaseModel):
    credential: Optional[str] = None  # Google ID token (JWT)
    access_token: Optional[str] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    google_id: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ValidateResetTokenRequest(BaseModel):
    token: str


class ValidateResetTokenResponse(BaseModel):
    valid: bool
    email: Optional[str] = None
    reason: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


class GenericAuthResponse(BaseModel):
    status: str = "success"
    message: str


class TestEmailRequest(BaseModel):
    email: EmailStr


class TestEmailResponse(BaseModel):
    status: str
    message: str
    recipient: str
    provider: Optional[str] = None
    resend_id: Optional[str] = None
    error: Optional[str] = None
    sender: Optional[str] = None

