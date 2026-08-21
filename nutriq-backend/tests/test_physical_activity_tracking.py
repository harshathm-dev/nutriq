import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app

def make_user():
    uid = uuid.uuid4().hex[:8]
    return {
        "name": f"Activity User {uid}",
        "email": f"activity_{uid}@example.com",
        "password": "SecurePassword123!"
    }

@pytest.mark.asyncio
async def test_physical_activity_tracking_lifecycle():
    user = make_user()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        reg_res = await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Setup Profile
        await client.post("/api/profile", headers=headers, json={
            "name": user["name"],
            "age": 28,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity_level": "moderately_active",
            "fitness_goal": "maintain",
            "dietary_preference": "standard"
        })

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 1. Initially verify daily summary has no exercise
        res = await client.get(f"/api/daily-summary?date={today_str}", headers=headers)
        assert res.status_code == 200
        daily_initial = res.json()
        assert daily_initial["exercise"]["logged"] is False
        assert daily_initial["exercise"]["calories_burned"] == 0.0
        assert daily_initial["exercise"]["items"] == []
        assert daily_initial["exercise"]["message"] == "No exercise logged today."

        # 2. Log an activity: Walking 30 mins (Moderate intensity) with steps, distance, notes
        # Formula: 3.5 * 3.5 * 70 / 200 * 30 = 128.6 kcal
        act_data = {
            "activity_type": "walking",
            "duration_minutes": 30,
            "intensity": "moderate",
            "steps": 4200,
            "distance_km": 3.1,
            "notes": "Morning park walk",
            "date": today_str,
            "time": "08:30"
        }
        res = await client.post("/api/activities", json=act_data, headers=headers)
        assert res.status_code == 201
        act1 = res.json()
        assert act1["type"] == "walking"
        assert act1["duration_min"] == 30
        assert act1["intensity"] == "moderate"
        assert act1["steps"] == 4200
        assert act1["distance_km"] == 3.1
        assert act1["notes"] == "Morning park walk"
        assert act1["calories_burned_est"] > 0
        act1_id = act1["id"]

        # 3. Log a second activity: Running (30 mins, moderate)
        # Formula: 9.8 * 3.5 * 70 / 200 * 30 = 360.2 kcal
        act2_data = {
            "type": "running",
            "duration_min": 30,
            "intensity": "moderate",
            "steps": 4800,
            "distance_km": 5.0,
            "notes": "Evening run",
            "date": today_str,
            "time": "18:00"
        }
        res = await client.post("/api/exercise", json=act2_data, headers=headers)
        assert res.status_code == 201
        act2 = res.json()
        assert act2["calories_burned_est"] > 300.0
        act2_id = act2["id"]

        # 4. Fetch list of activities for today
        res = await client.get(f"/api/activities?date={today_str}", headers=headers)
        assert res.status_code == 200
        activities = res.json()
        assert len(activities) >= 2
        act_ids = [a["id"] for a in activities]
        assert act1_id in act_ids
        assert act2_id in act_ids

        # 5. Verify Daily Summary reflection
        res = await client.get(f"/api/daily-summary?date={today_str}", headers=headers)
        assert res.status_code == 200
        daily_after = res.json()
        assert daily_after["exercise"]["logged"] is True
        assert daily_after["exercise"]["duration_minutes"] >= 60
        expected_burned = act1["calories_burned_est"] + act2["calories_burned_est"]
        assert abs(daily_after["exercise"]["calories_burned"] - expected_burned) < 1.0
        assert len(daily_after["exercise"]["items"]) >= 2

        # Check item details structure
        first_item = next(i for i in daily_after["exercise"]["items"] if i["id"] == act1_id)
        assert first_item["type"] == "walking"
        assert first_item["duration_min"] == 30
        assert first_item["intensity"] == "moderate"
        assert first_item["time"] != ""

        # Check calorie balance fields
        assert daily_after["calories"]["burned"] == daily_after["exercise"]["calories_burned"]
        assert daily_after["calories"]["net"] == round(daily_after["calories"]["consumed"] - daily_after["calories"]["burned"], 1)

        # 6. Test Duration Validation: Duration <= 0 should fail
        bad_data = {
            "activity_type": "running",
            "duration_minutes": 0
        }
        res = await client.post("/api/activities", json=bad_data, headers=headers)
        assert res.status_code in [400, 422]

        # 7. Update activity: change duration of act1 to 60 mins and intensity to high
        res = await client.put(f"/api/activities/{act1_id}", json={"duration_minutes": 60, "intensity": "high"}, headers=headers)
        assert res.status_code == 200
        updated_act = res.json()
        assert updated_act["duration_min"] == 60
        assert updated_act["intensity"] == "high"

        # 8. Weekly Summary reflection
        res = await client.get("/api/weekly-summary", headers=headers)
        assert res.status_code == 200
        weekly = res.json()
        assert weekly["summary"]["total_calories_burned"] > 0
        assert weekly["summary"]["total_active_minutes"] >= 90
        assert weekly["summary"]["active_days_count"] >= 1

        # 9. Delete activity and confirm daily summary recalculates
        res = await client.delete(f"/api/activities/{act1_id}", headers=headers)
        assert res.status_code == 204

        res = await client.delete(f"/api/exercise/{act2_id}", headers=headers)
        assert res.status_code == 204

        # Confirm deletion in daily summary
        res = await client.get(f"/api/daily-summary?date={today_str}", headers=headers)
        assert res.status_code == 200
        daily_final = res.json()
        assert daily_final["exercise"]["logged"] is False
        assert daily_final["exercise"]["calories_burned"] == 0.0
        assert daily_final["exercise"]["items"] == []

@pytest.mark.asyncio
async def test_offline_activity_sync_and_user_isolation():
    userA = make_user()
    userB = make_user()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register User A
        regA = await client.post("/api/auth/register", json={
            "name": userA["name"],
            "email": userA["email"],
            "password": userA["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        tokenA = regA.json()["access_token"]
        headersA = {"Authorization": f"Bearer {tokenA}"}

        # Register User B
        regB = await client.post("/api/auth/register", json={
            "name": userB["name"],
            "email": userB["email"],
            "password": userB["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        tokenB = regB.json()["access_token"]
        headersB = {"Authorization": f"Bearer {tokenB}"}

        # Offline sync batch for User A: Insert Cycling activity
        ex_id = "ex_offline_" + uuid.uuid4().hex[:8]
        sync_payload = {
            "device_id": "device_user_a",
            "changes": [
                {
                    "entity_type": "exercise",
                    "entity_id": ex_id,
                    "operation": "INSERT",
                    "payload": {
                        "type": "cycling",
                        "duration_min": 45,
                        "intensity": "moderate",
                        "calories_burned_est": 260.0
                    },
                    "client_timestamp": datetime.now(timezone.utc).isoformat()
                }
            ]
        }
        sync_res = await client.post("/api/sync", json=sync_payload, headers=headersA)
        assert sync_res.status_code == 200
        assert sync_res.json()["processed_count"] >= 1

        # Verify User A sees the synchronized activity
        resA = await client.get("/api/activities", headers=headersA)
        assert resA.status_code == 200
        actsA = resA.json()
        assert any(a["id"] == ex_id for a in actsA)

        # Verify User B does NOT see User A's synchronized activity
        resB = await client.get("/api/activities", headers=headersB)
        assert resB.status_code == 200
        actsB = resB.json()
        assert not any(a["id"] == ex_id for a in actsB)
