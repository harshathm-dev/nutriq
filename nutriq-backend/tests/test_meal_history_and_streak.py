import pytest
import uuid
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import httpx
from app.main import app
from app.database.session import AsyncSessionLocal
from app.services.streak_service import StreakService
from app.services.meal_service import MealService
from app.services.ai_service import AIService
from app.services.gemini_service import GeminiService
from app.models.meal import Meal, MealItem
from app.models.base import utc_now


@pytest.mark.asyncio
async def test_meal_history_and_streak_complete_suite():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User
        uid = uuid.uuid4().hex[:8]
        reg = await client.post("/api/auth/register", json={
            "name": "Meal & Streak User",
            "email": f"history_streak_{uid}@example.com",
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Setup Profile
        prof_res = await client.post("/api/profile", headers=headers, json={
            "name": "Meal & Streak User",
            "age": 28,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 72.0,
            "activity_level": "moderately_active",
            "fitness_goal": "maintain",
            "dietary_preference": "vegetarian"
        })
        assert prof_res.status_code in [200, 201]
        user_id = prof_res.json()["user_id"]

        # 2. Check initial state of Today's Meals & Streak
        init_today = await client.get("/api/meals/today", headers=headers)
        assert init_today.status_code == 200
        assert init_today.json() == []

        init_st = await client.get("/api/streak", headers=headers)
        assert init_st.status_code == 200
        assert init_st.json()["current_streak"] == 0
        assert init_st.json()["completed_today"] is False

        # 3. Log a Past Meal (e.g. 2 days ago) directly to DB
        tz = ZoneInfo("Asia/Kolkata")
        today_local = datetime.now(tz).date()
        two_days_ago_local = today_local - timedelta(days=2)
        yesterday_local = today_local - timedelta(days=1)

        past_time_utc = datetime(two_days_ago_local.year, two_days_ago_local.month, two_days_ago_local.day, 8, 30, tzinfo=tz).astimezone(timezone.utc)
        yesterday_time_utc = datetime(yesterday_local.year, yesterday_local.month, yesterday_local.day, 12, 30, tzinfo=tz).astimezone(timezone.utc)

        async with AsyncSessionLocal() as session:
            # 2 days ago meal
            past_meal = Meal(
                user_id=user_id,
                meal_type="breakfast",
                occurred_at=past_time_utc,
                source="search"
            )
            session.add(past_meal)
            await session.flush()
            past_item = MealItem(
                meal_id=past_meal.id,
                food_name="Oatmeal with Almonds",
                quantity=1.0,
                serving_unit="bowl",
                grams=250.0,
                calories=320.0,
                protein_g=12.0,
                carbs_g=48.0,
                fat_g=8.0,
                fiber_g=6.0
            )
            session.add(past_item)

            # Yesterday meal
            yest_meal = Meal(
                user_id=user_id,
                meal_type="lunch",
                occurred_at=yesterday_time_utc,
                source="search"
            )
            session.add(yest_meal)
            await session.flush()
            yest_item = MealItem(
                meal_id=yest_meal.id,
                food_name="Paneer Butter Masala & Roti",
                quantity=1.0,
                serving_unit="plate",
                grams=350.0,
                calories=580.0,
                protein_g=22.0,
                carbs_g=55.0,
                fat_g=28.0,
                fiber_g=5.0
            )
            session.add(yest_item)
            await session.commit()

        # 4. Verify Today's Meals endpoint strictly returns NO past meals
        today_check1 = await client.get("/api/meals/today", headers=headers)
        assert today_check1.status_code == 200
        assert len(today_check1.json()) == 0  # Past meals must NEVER appear in today's meals!

        # 5. Log Today's First Meal (Breakfast at 08:00 AM)
        m1_res = await client.post("/api/meals", headers=headers, json={
            "meal_type": "breakfast",
            "source": "search",
            "items": [{
                "food_name": "Idli with Sambar",
                "quantity": 2.0,
                "serving_unit": "pieces",
                "grams": 160.0,
                "calories": 240.0,
                "protein_g": 8.0,
                "carbs_g": 46.0,
                "fat_g": 2.0,
                "fiber_g": 4.0
            }]
        })
        assert m1_res.status_code == 201
        m1_id = m1_res.json()["id"]

        # Log Today's Second Meal (Also Breakfast / Second Breakfast at 09:30 AM - tests duplicate meal_type support!)
        m2_res = await client.post("/api/meals", headers=headers, json={
            "meal_type": "breakfast",
            "source": "search",
            "items": [{
                "food_name": "Filter Coffee",
                "quantity": 1.0,
                "serving_unit": "cup",
                "grams": 150.0,
                "calories": 90.0,
                "protein_g": 3.0,
                "carbs_g": 10.0,
                "fat_g": 4.0,
                "fiber_g": 0.0
            }]
        })
        assert m2_res.status_code == 201
        m2_id = m2_res.json()["id"]

        # Log Today's Third Meal (Lunch at 01:00 PM)
        m3_res = await client.post("/api/meals", headers=headers, json={
            "meal_type": "lunch",
            "source": "search",
            "items": [{
                "food_name": "Dal Tadka with Steamed Rice",
                "quantity": 1.0,
                "serving_unit": "thali",
                "grams": 400.0,
                "calories": 520.0,
                "protein_g": 18.0,
                "carbs_g": 84.0,
                "fat_g": 12.0,
                "fiber_g": 7.0
            }]
        })
        assert m3_res.status_code == 201
        m3_id = m3_res.json()["id"]

        # 6. Verify GET /api/meals/today:
        # - Contains exactly 3 meals
        # - Contains both breakfast meals without overwriting
        # - Sorted chronologically (m1, then m2, then m3)
        today_res = await client.get("/api/meals/today", headers=headers)
        assert today_res.status_code == 200
        today_meals = today_res.json()
        assert len(today_meals) == 3
        assert [m["id"] for m in today_meals] == [m1_id, m2_id, m3_id]
        assert today_meals[0]["items"][0]["food_name"] == "Idli with Sambar"
        assert today_meals[1]["items"][0]["food_name"] == "Filter Coffee"
        assert today_meals[2]["items"][0]["food_name"] == "Dal Tadka with Steamed Rice"

        # 7. Check Streak Status (Should be active today!)
        streak_res = await client.get("/api/streak", headers=headers)
        assert streak_res.status_code == 200
        streak_data = streak_res.json()
        assert streak_data["completed_today"] is True
        # Since yesterday and 2 days ago were also logged, streak is 3 consecutive days!
        assert streak_data["current_streak"] == 3
        assert streak_data["longest_streak"] >= 3

        # 8. Test Day-Wise Meal History: GET /api/meals/history?date=...
        # A. History for Today
        hist_today = await client.get(f"/api/meals/history?date={today_local.isoformat()}", headers=headers)
        assert hist_today.status_code == 200
        h_today_data = hist_today.json()
        assert h_today_data["is_today"] is True
        assert h_today_data["meal_count"] == 3
        assert h_today_data["total_calories"] == (240 + 90 + 520)  # 850 kcal
        assert h_today_data["total_protein"] == (8.0 + 3.0 + 18.0)  # 29.0 g
        assert len(h_today_data["meals"]) == 3

        # B. History for Yesterday
        hist_yest = await client.get(f"/api/meals/history?date={yesterday_local.isoformat()}", headers=headers)
        assert hist_yest.status_code == 200
        h_yest_data = hist_yest.json()
        assert h_yest_data["is_today"] is False
        assert h_yest_data["meal_count"] == 1
        assert h_yest_data["total_calories"] == 580.0
        assert h_yest_data["total_protein"] == 22.0

        # C. History for an Empty Day (e.g. 5 days ago)
        empty_date = (today_local - timedelta(days=5)).isoformat()
        hist_empty = await client.get(f"/api/meals/history?date={empty_date}", headers=headers)
        assert hist_empty.status_code == 200
        h_empty_data = hist_empty.json()
        assert h_empty_data["meal_count"] == 0
        assert h_empty_data["total_calories"] == 0.0
        assert h_empty_data["has_data"] is False

        # 9. Test Multi-Day Range: GET /api/meals/history/range
        start_iso = (today_local - timedelta(days=6)).isoformat()
        end_iso = today_local.isoformat()
        range_res = await client.get(f"/api/meals/history/range?start_date={start_iso}&end_date={end_iso}", headers=headers)
        assert range_res.status_code == 200
        range_data = range_res.json()
        assert len(range_data["days"]) == 7
        assert range_data["total_meals"] == 5  # 1 (2-days-ago) + 1 (yesterday) + 3 (today)

        # 10. Test Edit Meal: PUT /api/meals/{meal_id}
        # Update Filter Coffee to have 2 cups (180 kcal) and rename meal_type to evening_snack
        edit_res = await client.put(f"/api/meals/{m2_id}", headers=headers, json={
            "meal_type": "snack",
            "items": [{
                "food_name": "Filter Coffee (Large)",
                "quantity": 2.0,
                "serving_unit": "cups",
                "grams": 300.0,
                "calories": 180.0,
                "protein_g": 6.0,
                "carbs_g": 20.0,
                "fat_g": 8.0,
                "fiber_g": 0.0
            }]
        })
        assert edit_res.status_code == 200
        edited = edit_res.json()
        assert edited["meal_type"] == "snack"
        assert len(edited["items"]) == 1
        assert edited["items"][0]["food_name"] == "Filter Coffee (Large)"
        assert edited["items"][0]["calories"] == 180.0

        # Verify edited meal reflects in today's history
        hist_today_after_edit = await client.get(f"/api/meals/history?date={today_local.isoformat()}", headers=headers)
        assert hist_today_after_edit.json()["total_calories"] == (240 + 180 + 520)  # 940 kcal

        # 11. Test Delete Meal: DELETE /api/meals/{meal_id}
        # Delete lunch meal (m3)
        del_res = await client.delete(f"/api/meals/{m3_id}", headers=headers)
        assert del_res.status_code == 204

        # Verify today's meals now only has 2 meals
        today_after_del = await client.get("/api/meals/today", headers=headers)
        assert today_after_del.status_code == 200
        assert len(today_after_del.json()) == 2
        assert [m["id"] for m in today_after_del.json()] == [m1_id, m2_id]

        # 12. Test AI Assistant Date Grounding & Context
        async with AsyncSessionLocal() as session:
            ai_ctx = await AIService.build_ai_context(session, user_id)
            assert "yesterday" in ai_ctx
            assert "yesterday_meals" in ai_ctx
            assert len(ai_ctx["yesterday_meals"]) == 1
            assert ai_ctx["yesterday_meals"][0]["items"][0]["food_name"] == "Paneer Butter Masala & Roti"
            assert len(ai_ctx["recent_meals"]) == 2

            # Test deterministic response for "what did i eat yesterday"
            resp_yesterday = await GeminiService.generate_assistant_response(
                user_message="What did I eat yesterday?",
                context=ai_ctx,
                candidate_foods=[]
            )
            assert "Paneer Butter Masala & Roti" in resp_yesterday["answer"]
            assert "580 kcal" in resp_yesterday["answer"]

            # Test deterministic response for "what did i eat today"
            resp_today = await GeminiService.generate_assistant_response(
                user_message="What did I eat today?",
                context=ai_ctx,
                candidate_foods=[]
            )
            assert "Idli with Sambar" in resp_today["answer"]
            assert "Filter Coffee (Large)" in resp_today["answer"]

