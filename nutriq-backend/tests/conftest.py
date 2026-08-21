import pytest
from sqlalchemy import text
from app.database.session import engine, Base, AsyncSessionLocal
from app.services.food_service import FoodService

@pytest.fixture(autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        migrations = [
            "ALTER TABLE allergies ADD COLUMN family_profile_id VARCHAR(36)",
            "ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'email'",
            "ALTER TABLE users ADD COLUMN google_id VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN welcome_email_sent BOOLEAN DEFAULT 0",
            "ALTER TABLE exercise ADD COLUMN intensity VARCHAR(50) DEFAULT 'moderate'"
        ]
        for m in migrations:
            try:
                await conn.execute(text(m))
            except Exception:
                pass

    async with AsyncSessionLocal() as session:
        await FoodService.seed_default_foods(session)
    yield
