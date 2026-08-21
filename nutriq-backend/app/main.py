from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database.session import engine, Base, AsyncSessionLocal
from app.services.food_service import FoodService

# Import all routers
from app.api.auth import router as auth_router
from app.api.profile import router as profile_router
from app.api.goals import router as goals_router
from app.api.calories import router as calories_router
from app.api.foods import router as foods_router
from app.api.meals import router as meals_router
from app.api.favorites import router as favorites_router
from app.api.tracking import router as tracking_router
from app.api.ai import router as ai_router
from app.api.analytics import router as analytics_router
from app.api.privacy import router as privacy_router
from app.api.export import router as export_router
from app.api.family import router as family_router
from app.api.billing import router as billing_router
from app.api.sync import router as sync_router
from app.api.daily_summary import router as daily_summary_router
from app.api.weekly_summary import router as weekly_summary_router
from app.api.reminders import router as reminders_router
from app.api.nutrition_status import router as nutrition_status_router
from app.api.streak import router as streak_router
from app.api.recommendations import router as recommendations_router
from app.api.insights import router as insights_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from sqlalchemy import text
    # Initialize DB tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Ensure required columns exist on SQLite database
        migrations = [
            "ALTER TABLE allergies ADD COLUMN family_profile_id VARCHAR(36)",
            "ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'email'",
            "ALTER TABLE users ADD COLUMN google_id VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN welcome_email_sent BOOLEAN DEFAULT 0",
            "ALTER TABLE exercise ADD COLUMN intensity VARCHAR(50) DEFAULT 'moderate'",
            "ALTER TABLE exercise ADD COLUMN steps INTEGER DEFAULT 0",
            "ALTER TABLE exercise ADD COLUMN distance_km FLOAT DEFAULT 0.0",
            "ALTER TABLE exercise ADD COLUMN notes VARCHAR(500)",
            "ALTER TABLE foods ADD COLUMN code VARCHAR(50)",
            "ALTER TABLE foods ADD COLUMN subcategory VARCHAR(100)",
            "ALTER TABLE foods ADD COLUMN region VARCHAR(100)",
            "ALTER TABLE foods ADD COLUMN serving_size_desc VARCHAR(100)",
            "ALTER TABLE foods ADD COLUMN calcium_mg FLOAT",
            "ALTER TABLE foods ADD COLUMN iron_mg FLOAT",
            "ALTER TABLE foods ADD COLUMN vitamin_c_mg FLOAT",
            "ALTER TABLE foods ADD COLUMN folate_ug FLOAT",
            "ALTER TABLE foods ADD COLUMN normalized_key VARCHAR(255)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_food_normalized_key ON foods(normalized_key)"
        ]
        for m in migrations:
            try:
                await conn.execute(text(m))
            except Exception:
                pass
    
    # Seed curated IFCT database
    async with AsyncSessionLocal() as session:
        await FoodService.seed_default_foods(session)

    yield

    # Clean shutdown
    await engine.dispose()

app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description="NutriQ Production API — Deterministic Nutrition & Agentic Intelligence Platform",
    lifespan=lifespan
)

# CORS middleware for React PWA frontend (Localhost & Vercel deployments)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5177",
        "http://127.0.0.1:5177",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://nutriq-7m0d6bv7h-nutriq.vercel.app",
        "https://nutriq-gules.vercel.app",
        "https://nutriq.vercel.app"
    ],
    allow_origin_regex=r"^(https:\/\/[a-zA-Z0-9_-]+\.vercel\.app|https:\/\/.*\.vercel\.app|http:\/\/(localhost|127\.0\.0\.1)(:\d+)?)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API routers under /api
api_prefix = settings.API_V1_PREFIX
app.include_router(auth_router, prefix=api_prefix)
app.include_router(profile_router, prefix=api_prefix)
app.include_router(goals_router, prefix=api_prefix)
app.include_router(calories_router, prefix=api_prefix)
app.include_router(foods_router, prefix=api_prefix)
app.include_router(meals_router, prefix=api_prefix)
app.include_router(favorites_router, prefix=api_prefix)
app.include_router(tracking_router, prefix=api_prefix)
app.include_router(ai_router, prefix=api_prefix)
app.include_router(analytics_router, prefix=api_prefix)
app.include_router(privacy_router, prefix=api_prefix)
app.include_router(export_router, prefix=api_prefix)
app.include_router(family_router, prefix=api_prefix)
app.include_router(billing_router, prefix=api_prefix)
app.include_router(sync_router, prefix=api_prefix)
app.include_router(daily_summary_router, prefix=api_prefix)
app.include_router(weekly_summary_router, prefix=api_prefix)
app.include_router(reminders_router, prefix=api_prefix)
app.include_router(nutrition_status_router, prefix=api_prefix)
app.include_router(streak_router, prefix=api_prefix)
app.include_router(recommendations_router, prefix=api_prefix)
app.include_router(insights_router, prefix=api_prefix)


from app.schemas.auth import TestEmailRequest, TestEmailResponse
from app.services.email_service import EmailService

@app.post("/api/test-email", response_model=TestEmailResponse, tags=["Development / Testing"])
async def test_email_endpoint(req: TestEmailRequest):
    """
    Diagnostic development endpoint to test welcome email delivery.
    Usage:
    POST /api/test-email
    {
        "email": "test@example.com"
    }
    """
    clean_email = str(req.email).lower().strip()
    result = EmailService.send_test_email(clean_email)
    
    if result.get("success"):
        return TestEmailResponse(
            status="success",
            message="Welcome email sent successfully! Please check your inbox and spam folder.",
            recipient=clean_email,
            provider=result.get("provider"),
            resend_id=result.get("id"),
            error=None,
            sender=result.get("from")
        )
    else:
        return TestEmailResponse(
            status="error",
            message="Failed to deliver welcome email via Resend.",
            recipient=clean_email,
            provider=result.get("provider"),
            resend_id=None,
            error=result.get("error"),
            sender=result.get("from")
        )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "2.0.0",
        "governing_standard": "NutriQ Master Specification v2.0"
    }

@app.get("/")
async def root():
    return {
        "message": "Welcome to NutriQ API",
        "docs": "/docs",
        "health": "/health"
    }
