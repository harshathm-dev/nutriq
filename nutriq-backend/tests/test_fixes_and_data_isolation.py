import pytest
from httpx import AsyncClient, ASGITransport
from datetime import date

from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.models.profile import UserProfile
from app.models.goal import Goal
from app.models.meal import Meal, MealItem
from app.models.tracking import Water, Exercise, WeightHistory
from app.models.reminder import MealReminderSetting
from app.utils.security import create_access_token, get_password_hash
import uuid
from app.models.base import utc_now


@pytest.mark.asyncio
async def test_user_data_isolation_e2e():
    """
    Validates complete data isolation between User A and User B.
    User B must NEVER see meals, water, weight, or daily summary belonging to User A.
    """
    uid_a = uuid.uuid4().hex[:8]
    uid_b = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as session:
        user_a = User(
            email=f"isolated_a_{uid_a}@nutriq.test",
            password_hash=get_password_hash("Password123!")
        )
        user_b = User(
            email=f"isolated_b_{uid_b}@nutriq.test",
            password_hash=get_password_hash("Password123!")
        )
        session.add_all([user_a, user_b])
        await session.commit()
        await session.refresh(user_a)
        await session.refresh(user_b)

        token_a = create_access_token({"sub": str(user_a.id), "email": user_a.email})
        token_b = create_access_token({"sub": str(user_b.id), "email": user_b.email})

        # Add profile & data for User A
        prof_a = UserProfile(
            user_id=user_a.id,
            name="User A",
            age=28,
            gender="male",
            height_cm=180.0,
            weight_kg=80.0,
            activity_level="moderately_active",
            fitness_goal="weight_loss",
            dietary_preference="standard"
        )
        session.add(prof_a)

        # Log Meal for User A
        meal_a = Meal(
            user_id=user_a.id,
            meal_type="breakfast",
            occurred_at=utc_now(),
            source="manual"
        )
        session.add(meal_a)
        await session.flush()

        item_a = MealItem(
            meal_id=meal_a.id,
            food_name="Plain Dosa",
            serving_unit="piece",
            quantity=2.0,
            grams=160.0,
            calories=270.0,
            protein_g=6.2,
            carbs_g=47.0,
            fat_g=6.0,
            fiber_g=2.8
        )
        session.add(item_a)

        # Log Water for User A
        water_a = Water(
            user_id=user_a.id,
            amount_ml=500.0,
            recorded_at=utc_now()
        )
        session.add(water_a)

        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Verify User A sees their meal
        res_a = await client.get("/api/meals", headers={"Authorization": f"Bearer {token_a}"})
        assert res_a.status_code == 200
        meals_a = res_a.json()
        assert len(meals_a) >= 1
        assert any(m["id"] == str(meal_a.id) for m in meals_a)

        # 2. Verify User B sees 0 meals (STRICT ISOLATION)
        res_b = await client.get("/api/meals", headers={"Authorization": f"Bearer {token_b}"})
        assert res_b.status_code == 200
        meals_b = res_b.json()
        assert len(meals_b) == 0

        # 3. Verify User B daily summary has 0 consumed calories
        sum_b = await client.get("/api/daily-summary", headers={"Authorization": f"Bearer {token_b}"})
        assert sum_b.status_code == 200
        data_b = sum_b.json()
        assert data_b["calories"]["consumed"] == 0.0
        assert data_b["hydration"]["consumed_ml"] == 0.0
        assert data_b["has_data"] is False

        # 4. Verify User B export has 0 meals
        exp_b = await client.get("/api/export/json", headers={"Authorization": f"Bearer {token_b}"})
        assert exp_b.status_code == 200
        exp_data_b = exp_b.json()
        assert len(exp_data_b["meals"]) == 0
        assert len(exp_data_b["water_logs"]) == 0

        # 5. Verify User B cannot delete User A's meal
        del_b = await client.delete(f"/api/meals/{meal_a.id}", headers={"Authorization": f"Bearer {token_b}"})
        assert del_b.status_code in [403, 404]


@pytest.mark.asyncio
async def test_dynamic_nutrition_insights_endpoint():
    """
    Validates GET /api/nutrition/insights returns dynamic data-grounded cards.
    """
    uid = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as session:
        user = User(
            email=f"insights_{uid}@nutriq.test",
            password_hash=get_password_hash("Password123!")
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_access_token({"sub": str(user.id), "email": user.email})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Fresh user with 0 meals -> returns clean empty / ready state
        res = await client.get("/api/nutrition/insights", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["has_data"] is False
        assert "insights" in data
        assert len(data["insights"]) >= 1
        assert data["insights"][0]["id"] == "no_meals_today"


@pytest.mark.asyncio
async def test_reminder_settings_persistence():
    """
    Validates reminder schedules persist and reload accurately.
    """
    uid = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as session:
        user = User(
            email=f"reminder_{uid}@nutriq.test",
            password_hash=get_password_hash("Password123!")
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_access_token({"sub": str(user.id), "email": user.email})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "reminders_enabled": True,
            "breakfast_enabled": True,
            "breakfast_time": "08:00",
            "lunch_enabled": True,
            "lunch_time": "13:00",
            "snack_enabled": True,
            "snack_time": "17:00",
            "dinner_enabled": True,
            "dinner_time": "20:00"
        }
        post_res = await client.put("/api/reminders/settings", json=payload, headers={"Authorization": f"Bearer {token}"})
        assert post_res.status_code == 200

        get_res = await client.get("/api/reminders/settings", headers={"Authorization": f"Bearer {token}"})
        assert get_res.status_code == 200
        settings_data = get_res.json()
        assert settings_data["breakfast_time"] == "08:00"
        assert settings_data["lunch_time"] == "13:00"
        assert settings_data["snack_time"] == "17:00"
        assert settings_data["dinner_time"] == "20:00"


@pytest.mark.asyncio
async def test_ai_candidate_foods_no_attribute_error():
    """
    Validates AI chat does not crash with AttributeError on Food candidate models.
    """
    uid = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as session:
        user = User(
            email=f"ai_{uid}@nutriq.test",
            password_hash=get_password_hash("Password123!")
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_access_token({"sub": str(user.id), "email": user.email})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/ai/chat",
            json={"messages": [{"role": "user", "content": "How many calories should dinner have?"}]},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "response" in data or "answer" in data
        assert len(data.get("response") or data.get("answer")) > 10
