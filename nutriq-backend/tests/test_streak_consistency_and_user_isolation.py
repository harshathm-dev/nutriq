import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from datetime import date, timedelta
from app.main import app

@pytest.mark.asyncio
async def test_streak_consistency_and_user_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User A
        uid_a = uuid.uuid4().hex[:6]
        email_a = f"streak_user_a_{uid_a}@example.com"
        pwd = "Password123!"
        res_a = await client.post("/api/auth/register", json={"email": email_a, "password": pwd})
        assert res_a.status_code == 201, f"Registration failed: {res_a.text}"
        token_a = res_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Initialize profile
        await client.post("/api/profile", headers=headers_a, json={
            "name": "Streak User A",
            "age": 28,
            "gender": "male",
            "height_cm": 178,
            "weight_kg": 75,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "vegetarian"
        })

        # Check initial streak for User A (must be 0)
        stk_init = await client.get("/api/streak", headers=headers_a)
        assert stk_init.status_code == 200
        data_init = stk_init.json()
        assert data_init["current_streak"] == 0
        assert data_init["longest_streak"] == 0
        assert data_init["total_active_days"] == 0
        assert data_init["completed_today"] is False

        # Compute Wednesday, Thursday, Friday dates of current week
        today = date.today()
        # Find Monday of current week
        monday = today - timedelta(days=today.weekday())
        wednesday = monday + timedelta(days=2)
        thursday = monday + timedelta(days=3)
        friday = monday + timedelta(days=4)

        # Ensure food item exists
        f_res = await client.post("/api/foods/custom", headers=headers_a, json={
            "name": "Streak Test Meal Food",
            "calories": 250,
            "protein_g": 15,
            "carbs_g": 30,
            "fat_g": 5,
            "fiber_g": 4,
            "serving_size": 100.0,
            "unit": "g"
        })
        assert f_res.status_code == 201
        food_id = f_res.json()["id"]

        # TEST 1: User A logs meals on Wednesday, Thursday, Friday
        meal_wed = await client.post("/api/meals", headers=headers_a, json={
            "meal_type": "lunch",
            "date": wednesday.isoformat(),
            "time": "13:00",
            "items": [{"food_id": food_id, "food_name": "Streak Test Meal Food", "calories": 250, "quantity": 1, "grams": 150}]
        })
        assert meal_wed.status_code == 201, f"Failed wed: {meal_wed.text}"

        meal_thu = await client.post("/api/meals", headers=headers_a, json={
            "meal_type": "lunch",
            "date": thursday.isoformat(),
            "time": "13:00",
            "items": [{"food_id": food_id, "food_name": "Streak Test Meal Food", "calories": 250, "quantity": 1, "grams": 150}]
        })
        assert meal_thu.status_code == 201, f"Failed thu: {meal_thu.text}"

        meal_fri = await client.post("/api/meals", headers=headers_a, json={
            "meal_type": "dinner",
            "date": friday.isoformat(),
            "time": "20:00",
            "items": [{"food_id": food_id, "food_name": "Streak Test Meal Food", "calories": 250, "quantity": 1, "grams": 150}]
        })
        assert meal_fri.status_code == 201, f"Failed fri: {meal_fri.text}"
        fri_meal_id = meal_fri.json()["id"]

        # Check Streak status for User A evaluated on Friday
        stk_fri = await client.get(f"/api/streak?current_date={friday.isoformat()}", headers=headers_a)
        assert stk_fri.status_code == 200
        data_fri = stk_fri.json()
        assert data_fri["current_streak"] == 3, f"Expected streak 3 on Friday, got {data_fri['current_streak']}"
        assert data_fri["longest_streak"] == 3
        assert data_fri["total_active_days"] == 3
        assert data_fri["completed_today"] is True

        # Verify weekly history has Wed, Thu, Fri marked Completed
        weekly_map = {item["day_name"]: item["completed"] for item in data_fri["weekly_history"]}
        assert weekly_map["Wed"] is True
        assert weekly_map["Thu"] is True
        assert weekly_map["Fri"] is True

        # TEST 2: Delete Friday's meal
        del_res = await client.delete(f"/api/meals/{fri_meal_id}", headers=headers_a)
        assert del_res.status_code == 204

        # Re-check Streak status evaluated on Friday (after deleting Friday's meal)
        stk_after_del = await client.get(f"/api/streak?current_date={friday.isoformat()}", headers=headers_a)
        assert stk_after_del.status_code == 200
        data_after_del = stk_after_del.json()
        # On Friday, without Friday meal, current streak is 2 (from Thursday & Wednesday)
        assert data_after_del["current_streak"] == 2
        assert data_after_del["total_active_days"] == 2
        assert data_after_del["completed_today"] is False
        weekly_map_after = {item["day_name"]: item["completed"] for item in data_after_del["weekly_history"]}
        assert weekly_map_after["Wed"] is True
        assert weekly_map_after["Thu"] is True
        assert weekly_map_after["Fri"] is False  # Friday is now Pending

        # TEST 3: Create a completely new User B
        uid_b = uuid.uuid4().hex[:6]
        email_b = f"streak_user_b_{uid_b}@example.com"
        res_b = await client.post("/api/auth/register", json={"email": email_b, "password": pwd})
        assert res_b.status_code == 201
        token_b = res_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Check User B streak (MUST be 0 with 0 days and clean weekly history)
        stk_b = await client.get("/api/streak", headers=headers_b)
        assert stk_b.status_code == 200
        data_b = stk_b.json()
        assert data_b["current_streak"] == 0
        assert data_b["longest_streak"] == 0
        assert data_b["total_active_days"] == 0
        assert data_b["completed_today"] is False
        for item in data_b["weekly_history"]:
            assert item["completed"] is False, f"User B should have no completed days, got {item}"

        # TEST 4: Login back to User A
        login_a = await client.post("/api/auth/login", json={"email": email_a, "password": pwd})
        assert login_a.status_code == 200
        headers_a_restored = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

        stk_a_restored = await client.get(f"/api/streak?current_date={friday.isoformat()}", headers=headers_a_restored)
        assert stk_a_restored.status_code == 200
        data_a_restored = stk_a_restored.json()
        assert data_a_restored["current_streak"] == 2
        assert data_a_restored["total_active_days"] == 2

        # TEST 5: Log Friday's meal again
        re_log_fri = await client.post("/api/meals", headers=headers_a_restored, json={
            "meal_type": "dinner",
            "date": friday.isoformat(),
            "time": "20:00",
            "items": [{"food_id": food_id, "food_name": "Streak Test Meal Food", "calories": 250, "quantity": 1, "grams": 150}]
        })
        assert re_log_fri.status_code == 201

        # Re-check Streak for User A
        stk_a_final = await client.get(f"/api/streak?current_date={friday.isoformat()}", headers=headers_a_restored)
        assert stk_a_final.status_code == 200
        data_a_final = stk_a_final.json()
        assert data_a_final["current_streak"] == 3
        assert data_a_final["total_active_days"] == 3
        assert data_a_final["completed_today"] is True
