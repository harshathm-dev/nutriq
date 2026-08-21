import pytest
import uuid
import json
from datetime import datetime, timezone, timedelta
import httpx
from app.main import app
from app.utils.date_utils import get_today_local


@pytest.mark.asyncio
async def test_daily_summary_and_reminders_and_google_auth():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # =====================================================================
        # 1. REGISTER USER A
        # =====================================================================
        uid = uuid.uuid4().hex[:6]
        user_email = f"summary_user_{uid}@example.com"
        reg_res = await client.post("/api/auth/register", json={
            "name": "Summary Tester",
            "email": user_email,
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Setup Profile & Goal
        await client.post("/api/profile", headers=headers, json={
            "name": "Summary Tester",
            "age": 28,
            "gender": "male",
            "height_cm": 178.0,
            "weight_kg": 75.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "standard"
        })

        await client.post("/api/goals", headers=headers, json={
            "goal_type": "weight_loss",
            "current_weight_kg": 75.0,
            "target_weight_kg": 70.0,
            "desired_rate": 0.5
        })

        today_d = get_today_local()
        today_str = today_d.isoformat()
        future_str = (today_d + timedelta(days=3)).isoformat()
        past_str = (today_d - timedelta(days=2)).isoformat()

        # =====================================================================
        # 2. TEST DAILY SUMMARY - EMPTY INITIAL STATE
        # =====================================================================
        init_sum = await client.get(f"/api/daily-summary?date={today_str}", headers=headers)
        assert init_sum.status_code == 200
        init_data = init_sum.json()
        assert init_data["has_data"] is False
        assert init_data["calories"]["consumed"] == 0.0
        assert init_data["hydration"]["consumed_ml"] == 0.0
        assert init_data["hydration"]["is_zero"] is True
        assert init_data["meals"]["breakfast"]["status_label"] == "Not logged"
        assert init_data["meals"]["lunch"]["status_label"] == "Not logged"
        assert init_data["meals"]["snack"]["status_label"] == "Not logged"
        assert init_data["meals"]["dinner"]["status_label"] == "Not logged"
        assert init_data["exercise"]["message"] == "No exercise logged today."
        assert init_data["progress_score"] is None  # No fake score on empty data

        # =====================================================================
        # 3. TEST DAILY SUMMARY - FUTURE DATE GUARD (NO FABRICATED DATA)
        # =====================================================================
        fut_sum = await client.get(f"/api/daily-summary?date={future_str}", headers=headers)
        assert fut_sum.status_code == 200
        fut_data = fut_sum.json()
        assert fut_data["is_future"] is True
        assert fut_data["has_data"] is False
        assert fut_data["empty_state_message"] == "No nutrition data available yet."
        assert fut_data["calories"]["consumed"] == 0.0
        assert fut_data["progress_score"] is None

        # =====================================================================
        # 4. LOG BREAKFAST, LUNCH, HYDRATION & EXERCISE FOR TODAY
        # =====================================================================
        # Breakfast: 2 Idlis (116 kcal) + 1 Sambar (141 kcal) = 257 kcal
        await client.post("/api/meals", headers=headers, json={
            "meal_type": "breakfast",
            "source": "search",
            "items": [
                {
                    "food_name": "Idli (Steamed Rice Cake)",
                    "quantity": 2.0,
                    "serving_unit": "piece",
                    "grams": 100.0,
                    "calories": 116.0,
                    "protein_g": 3.6,
                    "carbs_g": 24.0,
                    "fat_g": 0.4,
                    "fiber_g": 1.2
                },
                {
                    "food_name": "Tamil Sambar (Drumstick, Shallots & Vegetables)",
                    "quantity": 1.0,
                    "serving_unit": "katori",
                    "grams": 150.0,
                    "calories": 141.0,
                    "protein_g": 6.8,
                    "carbs_g": 20.2,
                    "fat_g": 3.4,
                    "fiber_g": 4.6
                }
            ]
        })

        # Lunch: 200g Rice (260 kcal) + 1 Boiled Egg (78 kcal) = 338 kcal
        await client.post("/api/meals", headers=headers, json={
            "meal_type": "lunch",
            "source": "search",
            "items": [
                {
                    "food_name": "White Rice (Cooked Ponni / Sona Masuri)",
                    "quantity": 1.0,
                    "serving_unit": "cup",
                    "grams": 200.0,
                    "calories": 260.0,
                    "protein_g": 5.4,
                    "carbs_g": 56.0,
                    "fat_g": 0.6,
                    "fiber_g": 1.4
                },
                {
                    "food_name": "Boiled Egg",
                    "quantity": 1.0,
                    "serving_unit": "piece",
                    "grams": 50.0,
                    "calories": 78.0,
                    "protein_g": 6.3,
                    "carbs_g": 0.6,
                    "fat_g": 5.3,
                    "fiber_g": 0.0
                }
            ]
        })

        # Hydration: 1,500 ml
        await client.post("/api/water", headers=headers, json={"amount_ml": 1500})

        # Exercise: 45 min Gym (240 kcal)
        ex_res = await client.post("/api/exercise", headers=headers, json={
            "type": "gym_workout",
            "duration_min": 45,
            "calories_burned_est": 240.0
        })
        assert ex_res.status_code == 201

        # =====================================================================
        # 5. TEST DAILY SUMMARY - GROUNDED VALUES AFTER LOGGING
        # =====================================================================
        logged_sum = await client.get(f"/api/daily-summary?date={today_str}", headers=headers)
        assert logged_sum.status_code == 200
        l_data = logged_sum.json()
        assert l_data["has_data"] is True
        assert l_data["calories"]["consumed"] == 595.0  # 257 + 338
        assert l_data["calories"]["burned"] == 240.0
        assert l_data["calories"]["net"] == 355.0  # 595 - 240
        assert l_data["calories"]["remaining"] > 0
        assert l_data["calories"]["is_over"] is False

        # Check macro percentages
        assert l_data["macros"]["protein"]["consumed"] == 22.1  # 3.6 + 6.8 + 5.4 + 6.3
        assert l_data["macros"]["protein"]["percentage"] > 0

        # Check Hydration
        assert l_data["hydration"]["consumed_ml"] == 1500.0
        assert l_data["hydration"]["is_zero"] is False

        # Check Meals Status
        assert l_data["meals"]["breakfast"]["logged"] is True
        assert l_data["meals"]["breakfast"]["status_label"] == "Logged"
        assert len(l_data["meals"]["breakfast"]["items"]) == 2

        assert l_data["meals"]["lunch"]["logged"] is True
        assert l_data["meals"]["lunch"]["status_label"] == "Logged"
        assert len(l_data["meals"]["lunch"]["items"]) == 2

        assert l_data["meals"]["dinner"]["logged"] is False
        assert l_data["meals"]["dinner"]["status_label"] == "Not logged"
        assert l_data["meals"]["logged_count"] == 2

        # Check Exercise
        assert l_data["exercise"]["logged"] is True
        assert l_data["exercise"]["duration_minutes"] == 45
        assert l_data["exercise"]["calories_burned"] == 240.0

        # Check Progress Score
        assert l_data["progress_score"] is not None
        assert 0 <= l_data["progress_score"] <= 100

        # =====================================================================
        # 6. TEST SMART MEAL REMINDER SETTINGS & API
        # =====================================================================
        # GET default settings
        rem_set = await client.get("/api/reminders/settings", headers=headers)
        assert rem_set.status_code == 200
        set_data = rem_set.json()
        assert set_data["reminders_enabled"] is True
        assert set_data["breakfast_time"] == "08:00"
        assert set_data["lunch_time"] == "13:00"
        assert set_data["dinner_time"] == "20:00"
        assert set_data["grace_period_minutes"] == 30

        # UPDATE settings
        upd_res = await client.put("/api/reminders/settings", headers=headers, json={
            "lunch_time": "12:30",
            "snack_enabled": False,
            "grace_period_minutes": 15
        })
        assert upd_res.status_code == 200
        assert upd_res.json()["lunch_time"] == "12:30"
        assert upd_res.json()["grace_period_minutes"] == 15

        # Check Pending Reminders (Breakfast and Lunch logged, Dinner not logged)
        # At 21:00 (past 20:00 + 15 min), dinner should trigger
        pending_res = await client.get(f"/api/reminders/pending?current_time={today_str}T21:00:00Z", headers=headers)
        assert pending_res.status_code == 200
        p_data = pending_res.json()
        assert p_data["has_pending"] is True
        assert p_data["meal_type"] == "dinner"
        assert "Dinner Reminder" in p_data["title"]
        assert "You haven't logged your dinner yet" in p_data["message"]

        # Test Reminder Action: Remind Me Later
        act_res = await client.post("/api/reminders/respond", headers=headers, json={
            "meal_type": "dinner",
            "action": "remind_later",
            "date": today_str
        })
        assert act_res.status_code == 200
        assert act_res.json()["remind_later_count"] == 1

        # Test Reminder Action: Dismiss
        dis_res = await client.post("/api/reminders/respond", headers=headers, json={
            "meal_type": "dinner",
            "action": "dismiss",
            "date": today_str
        })
        assert dis_res.status_code == 200
        assert dis_res.json()["dismissed"] is True

        # Now pending returns Daily Summary reminder (due at 20:30)
        pending_after = await client.get("/api/reminders/pending?current_time=2026-08-19T21:00:00Z", headers=headers)
        assert pending_after.status_code == 200
        assert pending_after.json()["has_pending"] is True
        assert pending_after.json()["meal_type"] == "daily_summary"
        assert "Daily Summary" in pending_after.json()["title"]

        # Dismiss daily summary reminder
        dis_sum = await client.post("/api/reminders/respond", headers=headers, json={
            "meal_type": "daily_summary",
            "action": "dismiss",
            "date": today_str
        })
        assert dis_sum.status_code == 200
        assert dis_sum.json()["dismissed"] is True

        # Now all reminders for the day are cleared
        pending_final = await client.get("/api/reminders/pending?current_time=2026-08-19T21:00:00Z", headers=headers)
        assert pending_final.status_code == 200
        assert pending_final.json()["has_pending"] is False

        # =====================================================================
        # 7. TEST GOOGLE SIGN-IN (EXISTING USER LINKING & NEW USER)
        # =====================================================================
        # Existing user linking
        g_exist = await client.post("/api/auth/google", json={
            "email": user_email,
            "name": "Summary Tester Google",
            "google_id": "google_sub_12345"
        })
        assert g_exist.status_code == 200
        exist_token = g_exist.json()["access_token"]
        assert g_exist.json()["email"] == user_email

        # Verify linked session access
        p_res = await client.get("/api/profile", headers={"Authorization": f"Bearer {exist_token}"})
        assert p_res.status_code == 200
        assert p_res.json()["name"] == "Summary Tester"  # Respects NutriQ profile

        # New Google User
        new_uid = uuid.uuid4().hex[:6]
        new_g_email = f"new_google_user_{new_uid}@gmail.com"
        g_new = await client.post("/api/auth/google", json={
            "email": new_g_email,
            "name": "New Google Explorer",
            "google_id": f"google_sub_{new_uid}"
        })
        assert g_new.status_code == 200
        new_token = g_new.json()["access_token"]
        assert g_new.json()["email"] == new_g_email

        # Verify new user profile is not yet completed (returns 404 or None before onboarding)
        new_prof_res = await client.get("/api/profile", headers={"Authorization": f"Bearer {new_token}"})
        assert new_prof_res.status_code in [200, 404]
        if new_prof_res.status_code == 200:
            assert new_prof_res.json() is None or new_prof_res.json() == {}
