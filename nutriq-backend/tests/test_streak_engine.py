import pytest
import uuid
from datetime import datetime, timezone, timedelta
import httpx
from app.main import app
from app.database.session import AsyncSessionLocal
from app.services.streak_service import StreakService
from app.models.meal import Meal, MealItem
from app.models.base import utc_now
from app.utils.date_utils import get_today_local


@pytest.mark.asyncio
async def test_streak_engine():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User
        uid = uuid.uuid4().hex[:8]
        reg = await client.post("/api/auth/register", json={
            "name": "Streak Tester",
            "email": f"streak_{uid}@example.com",
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Setup Profile
        prof_res = await client.post("/api/profile", headers=headers, json={
            "name": "Streak Tester",
            "age": 25,
            "gender": "female",
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity_level": "lightly_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "vegetarian"
        })
        assert prof_res.status_code in [200, 201]
        user_id = prof_res.json()["user_id"]



        # 2. Initial Streak Check (New user: streak = 0, completed_today = False)
        init_st = await client.get("/api/streak", headers=headers)
        assert init_st.status_code == 200
        st_data = init_st.json()
        assert st_data["current_streak"] == 0
        assert st_data["longest_streak"] == 0
        assert st_data["completed_today"] is False
        assert len(st_data["weekly_history"]) == 7

        # 3. Log a Meal Today -> streak should become 1
        today_date_str = get_today_local().isoformat()
        meal_res = await client.post("/api/meals", headers=headers, json={
            "meal_type": "breakfast",
            "source": "search",
            "date": today_date_str,
            "items": [{
                "food_name": "Idli",
                "quantity": 2.0,
                "serving_unit": "piece",
                "grams": 100.0,
                "calories": 130.0,
                "protein_g": 4.0,
                "carbs_g": 26.0,
                "fat_g": 0.5,
                "fiber_g": 1.5
            }]
        })
        assert meal_res.status_code == 201

        # Verify streak updated to 1
        st_after_meal = await client.get("/api/streak", headers=headers)
        assert st_after_meal.status_code == 200
        d1 = st_after_meal.json()
        assert d1["current_streak"] == 1
        assert d1["longest_streak"] == 1
        assert d1["total_active_days"] == 1
        assert d1["completed_today"] is True

        # 4. Log Water and Exercise on same day -> streak must still be 1 (no duplicate increment)
        await client.post("/api/tracking/water", headers=headers, json={"amount_ml": 500.0})
        await client.post("/api/tracking/exercise", headers=headers, json={
            "type": "walking",
            "duration_min": 30,
            "intensity": "moderate"
        })

        st_same_day = await client.get("/api/streak", headers=headers)
        d_same = st_same_day.json()
        assert d_same["current_streak"] == 1
        assert d_same["total_active_days"] == 1

        # 5. Simulate Yesterday + Day Before Yesterday Logs for Milestone Testing
        async with AsyncSessionLocal() as db_session:
            tz = await StreakService.get_user_timezone(db_session, user_id)
            today = get_today_local(str(tz))

            # Insert meal on Day -2 (2 days ago)
            d_minus_2 = today - timedelta(days=2)
            d_minus_2_dt = datetime(d_minus_2.year, d_minus_2.month, d_minus_2.day, 12, 0, 0, tzinfo=tz).astimezone(timezone.utc)
            m2 = Meal(user_id=user_id, meal_type="lunch", occurred_at=d_minus_2_dt, created_at=utc_now())
            db_session.add(m2)

            # Insert meal on Day -1 (yesterday)
            d_minus_1 = today - timedelta(days=1)
            d_minus_1_dt = datetime(d_minus_1.year, d_minus_1.month, d_minus_1.day, 12, 0, 0, tzinfo=tz).astimezone(timezone.utc)
            m1 = Meal(user_id=user_id, meal_type="lunch", occurred_at=d_minus_1_dt, created_at=utc_now())
            db_session.add(m1)

            # Reset streak state to day -1 with streak=2
            streak_rec = await StreakService.get_or_create_streak(db_session, user_id)
            streak_rec.last_completed_date = d_minus_1.isoformat()
            streak_rec.current_streak = 2
            streak_rec.longest_streak = 2
            streak_rec.total_active_days = 2
            await db_session.commit()

        # 6. Check streak via API: Day -2, Day -1, and Today are all completed -> Streak = 3!
        st_3day = await client.post("/api/streak/check", headers=headers)
        assert st_3day.status_code == 200
        d3 = st_3day.json()
        assert d3["current_streak"] == 3
        assert d3["longest_streak"] == 3
        assert d3["new_milestone"] == 3  # Hit 3-day milestone!

        # 7. Acknowledge Milestone
        ack_res = await client.post("/api/streak/milestone-ack", headers=headers, json={"milestone": 3})
        assert ack_res.status_code == 200
        assert ack_res.json()["acknowledged"] is True

        # Subsequent check should not report milestone 3 again
        st_subseq = await client.get("/api/streak", headers=headers)
        assert st_subseq.json()["new_milestone"] is None
        assert 3 in st_subseq.json()["milestones_achieved"]

        # 8. Check History Endpoint
        hist_res = await client.get("/api/streak/history", headers=headers)
        assert hist_res.status_code == 200
        hist_data = hist_res.json()
        assert hist_data["current_streak"] == 3
        assert len(hist_data["history"]) == 7
