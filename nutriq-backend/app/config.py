import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_path = os.path.join(_backend_root, ".env")
load_dotenv(_env_path)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_path, extra="ignore")

    APP_NAME: str = "NutriQ Backend"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./nutriq.db"
    
    # Security & Auth
    JWT_SECRET: str = "nutriq-super-secure-production-secret-key-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # AI Provider & Controls
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.6-flash"
    ANTHROPIC_API_KEY: Optional[str] = None
    AI_DEFAULT_MODEL: str = "gemini-3.6-flash"
    AI_FAST_MODEL: str = "gemini-3.6-flash"
    AI_DAILY_LIMIT_FREE: int = 15
    AI_DAILY_LIMIT_PREMIUM: int = 200
    
    # Deterministic Engine Constants
    SAFE_MIN_CALORIES: int = 1200
    SAFE_MAX_CALORIES: int = 5000
    GOAL_RULE_VERSION: str = "2.0"
    
    # App & Frontend URL
    APP_URL: str = "http://localhost:5173"
    
    # Email Service Configuration
    EMAIL_PROVIDER: str = "resend"  # "resend", "smtp", "console", "mock"
    RESEND_API_KEY: Optional[str] = None
    WELCOME_EMAIL_FROM: str = "NutriQ <onboarding@resend.dev>"
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    EMAIL_FROM: str = "NutriQ <no-reply@nutriq.app>"
    
    # Password Reset & Rate Limiting
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    FORGOT_PASSWORD_RATE_LIMIT_SECONDS: int = 60
    
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:5173"

    # Third party / External mocks / integrations
    VISION_API_KEY: Optional[str] = None
    SPEECH_API_KEY: Optional[str] = None
    SENTRY_DSN: Optional[str] = None
    FCM_CONFIG: Optional[str] = None
    BILLING_PROVIDER_KEY: Optional[str] = None

settings = Settings()
