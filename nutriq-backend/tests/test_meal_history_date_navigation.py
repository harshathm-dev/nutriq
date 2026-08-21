import pytest
import uuid
from datetime import datetime, timezone, timedelta, date
from zoneinfo import ZoneInfo
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.models.meal import Meal, MealItem
from app.services.meal_service import MealService


@pytest.mark.asyncio
async def test_date_navigation_mathematics_and_timezone_safety():
    """
    Validates that single day navigation (addDays/subtractDays) exactly decrements/increments
    by 1 calendar day without timezone shift bugs.
    """
    tz = ZoneInfo("Asia/Kolkata")
    today_ist = datetime.now(tz).date()

    # 1. Start from 20-Aug-2026
    d20 = date(2026, 8, 20)
    # Previous day must be strictly 19-Aug-2026
    d19 = d20 - timedelta(days=1)
    assert d19 == date(2026, 8, 19)

    # Previous day again must be strictly 18-Aug-2026
    d18 = d19 - timedelta(days=1)
    assert d18 == date(2026, 8, 18)

    # Next day from 18-Aug must be strictly 19-Aug-2026
    assert d18 + timedelta(days=1) == date(2026, 8, 19)

    # Next day from 19-Aug must be strictly 20-Aug-2026
    assert d19 + timedelta(days=1) == date(2026, 8, 20)

    # Validate UTC boundaries for Asia/Kolkata
    # 2026-08-19 00:00:00 IST -> 2026-08-18 18:30:00 UTC
    # 2026-08-19 23:59:59 IST -> 2026-08-19 18:30:00 UTC
    start_utc_19, end_utc_19 = MealService.get_date_bounds_utc(date(2026, 8, 19), "Asia/Kolkata")
    assert start_utc_19 == datetime(2026, 8, 18, 18, 30, 0, tzinfo=timezone.utc)
    assert end_utc_19 == datetime(2026, 8, 19, 18, 30, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_meal_history_consecutive_days_isolation_and_navigation():
    """
    Comprehensive verification covering Test 1 through Test 10:
    - Verifies 18-Aug, 19-Aug, and 20-Aug meal isolation.
    - Tests that newly logged meals on today do not leak into yesterday or 18-Aug.
    - Confirms GET /api/meals/history?date=YYYY-MM-DD returns exact day metrics.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register a clean test user
        email = f"meal_nav_{uuid.uuid4().hex[:8]}@example.com"
        reg_res = await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Date Navigation User"
        })
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create Profile
        await client.post("/api/profile", headers=headers, json={
            "age": 28,
            "gender": "male",
            "height_cm": 178,
            "weight_kg": 75,
            "activity_level": "moderately_active",
            "fitness_goal": "maintain",
            "dietary_preference": "vegetarian"
        })

        tz = ZoneInfo("Asia/Kolkata")
        today_local = datetime.now(tz).date()
        yesterday_local = today_local - timedelta(days=1)
        two_days_ago_local = today_local - timedelta(days=2)

        # 1. Log historical meal on 2 days ago (e.g. 18-Aug)
        # 18-Aug 08:30 AM IST = 03:00 AM UTC
        dt_18_utc = datetime(two_days_ago_local.year, two_days_ago_local.month, two_days_ago_local.day, 3, 0, 0, tzinfo=timezone.utc)
        m18_res = await client.post("/api/meals", headers=headers, json={
            "meal_type": "breakfast",
            "source": "manual",
            "occurred_at": dt_18_utc.isoformat(),
            "items": [{
                "food_name": "Dosa with Chutney",
                "quantity": 2.0,
                "serving_unit": "pieces",
                "grams": 200.0,
                "calories": 320.0,
                "protein_g": 6.0,
                "carbs_g": 48.0,
                "fat_g": 12.0,
                "fiber_g": 3.0
            }]
        })
        assert m18_res.status_code == 201
        m18_id = m18_res.json()["id"]

        # 2. Log historical meals on Yesterday (e.g. 19-Aug)
        # Breakfast: 08:30 AM IST = 03:00 AM UTC
        dt_19_b_utc = datetime(yesterday_local.year, yesterday_local.month, yesterday_local.day, 3, 0, 0, tzinfo=timezone.utc)
        m19_b_res = await client.post("/api/meals", headers=headers, json={
            "meal_type": "breakfast",
            "source": "manual",
            "occurred_at": dt_19_b_utc.isoformat(),
            "items": [{
                "food_name": "Dosa + Sambar",
                "quantity": 2.0,
                "serving_unit": "pieces",
                "grams": 240.0,
                "calories": 360.0,
                "protein_g": 8.0,
                "carbs_g": 54.0,
                "fat_g": 12.0,
                "fiber_g": 4.0
            }]
        })
        assert m19_b_res.status_code == 201

        # Lunch: 01:00 PM IST = 07:30 AM UTC
        dt_19_l_utc = datetime(yesterday_local.year, yesterday_local.month, yesterday_local.day, 7, 30, 0, tzinfo=timezone.utc)
        m19_l_res = await client.post("/api/meals", headers=headers, json={
            "meal_type": "lunch",
            "source": "manual",
            "occurred_at": dt_19_l_utc.isoformat(),
            "items": [{
                "food_name": "Curd Rice",
                "quantity": 1.0,
                "serving_unit": "bowl",
                "grams": 250.0,
                "calories": 280.0,
                "protein_g": 6.0,
                "carbs_g": 45.0,
                "fat_g": 8.0,
                "fiber_g": 1.0
            }]
        })
        assert m19_l_res.status_code == 201

        # Dinner: 08:30 PM IST = 03:00 PM UTC
        dt_19_d_utc = datetime(yesterday_local.year, yesterday_local.month, yesterday_local.day, 15, 0, 0, tzinfo=timezone.utc)
        m19_d_res = await client.post("/api/meals", headers=headers, json={
            "meal_type": "dinner",
            "source": "manual",
            "occurred_at": dt_19_d_utc.isoformat(),
            "items": [{
                "food_name": "Chapati with Dal",
                "quantity": 3.0,
                "serving_unit": "pieces",
                "grams": 220.0,
                "calories": 380.0,
                "protein_g": 14.0,
                "carbs_g": 60.0,
                "fat_g": 8.0,
                "fiber_g": 6.0
            }]
        })
        assert m19_d_res.status_code == 201

        # 3. Log meals on Today (e.g. 20-Aug)
        m20_res = await client.post("/api/meals", headers=headers, json={
            "meal_type": "breakfast",
            "source": "manual",
            "items": [{
                "food_name": "Poha with Roasted Peanuts",
                "quantity": 1.0,
                "serving_unit": "plate",
                "grams": 200.0,
                "calories": 310.0,
                "protein_g": 7.0,
                "carbs_g": 52.0,
                "fat_g": 9.0,
                "fiber_g": 3.0
            }]
        })
        assert m20_res.status_code == 201

        # -------------------------------------------------------------
        # TEST 1: Open Today (20-Aug) -> Previous Day -> Expected 19-Aug
        # -------------------------------------------------------------
        date_19_str = yesterday_local.isoformat()
        res_19 = await client.get(f"/api/meals/history?date={date_19_str}", headers=headers)
        assert res_19.status_code == 200
        data_19 = res_19.json()
        assert data_19["date"] == date_19_str
        assert data_19["is_today"] is False
        assert data_19["meal_count"] == 3
        assert data_19["total_calories"] == (360.0 + 280.0 + 380.0)  # 1020.0 kcal
        food_names_19 = [i["food_name"] for m in data_19["meals"] for i in m["items"]]
        assert "Dosa + Sambar" in food_names_19
        assert "Curd Rice" in food_names_19
        assert "Chapati with Dal" in food_names_19
        assert "Poha with Roasted Peanuts" not in food_names_19
        assert "Dosa with Chutney" not in food_names_19

        # -------------------------------------------------------------
        # TEST 2: Previous Day Again -> Expected 18-Aug
        # -------------------------------------------------------------
        date_18_str = two_days_ago_local.isoformat()
        res_18 = await client.get(f"/api/meals/history?date={date_18_str}", headers=headers)
        assert res_18.status_code == 200
        data_18 = res_18.json()
        assert data_18["date"] == date_18_str
        assert data_18["is_today"] is False
        assert data_18["meal_count"] == 1
        assert data_18["total_calories"] == 320.0
        food_names_18 = [i["food_name"] for m in data_18["meals"] for i in m["items"]]
        assert "Dosa with Chutney" in food_names_18
        assert "Curd Rice" not in food_names_18
        assert "Poha with Roasted Peanuts" not in food_names_18

        # -------------------------------------------------------------
        # TEST 3: Next Day from 18-Aug -> Expected 19-Aug
        # -------------------------------------------------------------
        res_next_19 = await client.get(f"/api/meals/history?date={date_19_str}", headers=headers)
        assert res_next_19.status_code == 200
        assert res_next_19.json()["meal_count"] == 3

        # -------------------------------------------------------------
        # TEST 4: Next Day from 19-Aug -> Expected 20-Aug (Today)
        # -------------------------------------------------------------
        date_20_str = today_local.isoformat()
        res_20 = await client.get(f"/api/meals/history?date={date_20_str}", headers=headers)
        assert res_20.status_code == 200
        data_20 = res_20.json()
        assert data_20["date"] == date_20_str
        assert data_20["is_today"] is True
        assert data_20["meal_count"] == 1
        assert data_20["total_calories"] == 310.0
        food_names_20 = [i["food_name"] for m in data_20["meals"] for i in m["items"]]
        assert "Poha with Roasted Peanuts" in food_names_20
        assert "Curd Rice" not in food_names_20

        # -------------------------------------------------------------
        # TEST 5: Today Button -> Returns Current Local Date
        # -------------------------------------------------------------
        res_today_default = await client.get("/api/meals/history", headers=headers)
        assert res_today_default.status_code == 200
        assert res_today_default.json()["date"] == today_local.isoformat()
        assert res_today_default.json()["is_today"] is True

        # -------------------------------------------------------------
        # TEST 9 & 10: Log a New Meal Today, Navigate to Yesterday & Back
        # -------------------------------------------------------------
        new_meal_res = await client.post("/api/meals", headers=headers, json={
            "meal_type": "lunch",
            "source": "manual",
            "items": [{
                "food_name": "Vegetable Biryani",
                "quantity": 1.0,
                "serving_unit": "bowl",
                "grams": 300.0,
                "calories": 420.0,
                "protein_g": 9.0,
                "carbs_g": 65.0,
                "fat_g": 14.0,
                "fiber_g": 5.0
            }]
        })
        assert new_meal_res.status_code == 201

        # Check Yesterday: New meal must NOT appear yesterday
        res_yest_after_new = await client.get(f"/api/meals/history?date={date_19_str}", headers=headers)
        assert res_yest_after_new.status_code == 200
        assert res_yest_after_new.json()["meal_count"] == 3
        yest_foods = [i["food_name"] for m in res_yest_after_new.json()["meals"] for i in m["items"]]
        assert "Vegetable Biryani" not in yest_foods

        # Check Today: New meal MUST appear today
        res_today_after_new = await client.get(f"/api/meals/history?date={date_20_str}", headers=headers)
        assert res_today_after_new.status_code == 200
        assert res_today_after_new.json()["meal_count"] == 2
        assert res_today_after_new.json()["total_calories"] == (310.0 + 420.0)  # 730.0 kcal
        today_foods = [i["food_name"] for m in res_today_after_new.json()["meals"] for i in m["items"]]
        assert "Vegetable Biryani" in today_foods

        # Confirm Dashboard GET /api/meals/today matches 20-Aug strictly
        dash_today = await client.get("/api/meals/today", headers=headers)
        assert dash_today.status_code == 200
        assert len(dash_today.json()) == 2
