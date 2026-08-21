import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app

async def create_test_user(client: AsyncClient, weight_kg: float = 80.0):
    email = f"water_user_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = await client.post("/api/auth/register", json={
        "name": "Water Test User",
        "email": email,
        "password": "Password123!",
        "terms_accepted": True,
        "ai_consent_accepted": True
    })
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/profile", headers=headers, json={
        "name": "Water Test User",
        "age": 30,
        "gender": "male",
        "height_cm": 180.0,
        "weight_kg": weight_kg,
        "activity_level": "moderately_active",
        "fitness_goal": "weight_loss",
        "dietary_preference": "standard"
    })
    return headers

@pytest.mark.asyncio
async def test_water_logging_quick_and_custom():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await create_test_user(client, weight_kg=80.0)
        today_str = datetime.now(timezone.utc).date().isoformat()

        # 1. Log 250 ml (Quick add)
        res1 = await client.post(
            "/api/water",
            json={"amount_ml": 250, "date": today_str, "time": "09:00"},
            headers=headers
        )
        assert res1.status_code == 201
        data1 = res1.json()
        assert data1["amount_ml"] == 250.0
        assert data1["date"] == today_str
        log1_id = data1["id"]

        # 2. Log 500 ml (Quick add)
        res2 = await client.post(
            "/api/water",
            json={"amount_ml": 500, "date": today_str, "time": "12:30"},
            headers=headers
        )
        assert res2.status_code == 201
        assert res2.json()["amount_ml"] == 500.0

        # 3. Log custom 750 ml
        res3 = await client.post(
            "/api/water",
            json={"amount_ml": 750, "date": today_str, "time": "15:45"},
            headers=headers
        )
        assert res3.status_code == 201
        assert res3.json()["amount_ml"] == 750.0

        # 4. Check today's summary (Target should be 80 * 35 = 2800 ml)
        res_today = await client.get(f"/api/water/today?date={today_str}", headers=headers)
        assert res_today.status_code == 200
        today_data = res_today.json()
        assert today_data["consumed_ml"] == 1500.0
        assert today_data["target_ml"] == 2800.0
        assert today_data["remaining_ml"] == 1300.0
        assert today_data["completion_percentage"] == round((1500 / 2800) * 100, 1)
        assert len(today_data["logs"]) == 3

        # 5. List with date query
        res_list = await client.get(f"/api/water?date={today_str}", headers=headers)
        assert res_list.status_code == 200
        logs = res_list.json()
        assert len(logs) == 3

        # 6. Delete a log entry
        res_del = await client.delete(f"/api/water/{log1_id}", headers=headers)
        assert res_del.status_code in [200, 204]

        # 7. Verify remaining total after deletion
        res_after_del = await client.get(f"/api/water/today?date={today_str}", headers=headers)
        assert res_after_del.status_code == 200
        assert res_after_del.json()["consumed_ml"] == 1250.0
        assert len(res_after_del.json()["logs"]) == 2

@pytest.mark.asyncio
async def test_water_validation_limits():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await create_test_user(client)

        # Negative amount
        res_neg = await client.post("/api/water", json={"amount_ml": -100}, headers=headers)
        assert res_neg.status_code == 422

        # Zero amount
        res_zero = await client.post("/api/water", json={"amount_ml": 0}, headers=headers)
        assert res_zero.status_code == 422

        # Exceeding maximum limit (> 5000 ml)
        res_huge = await client.post("/api/water", json={"amount_ml": 6000}, headers=headers)
        assert res_huge.status_code == 422

@pytest.mark.asyncio
async def test_water_user_isolation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        today_str = datetime.now(timezone.utc).date().isoformat()
        headers_u1 = await create_test_user(client, weight_kg=80.0)
        headers_u2 = await create_test_user(client, weight_kg=60.0)

        # User 1 logs 500 ml
        res1 = await client.post(
            "/api/water",
            json={"amount_ml": 500, "date": today_str, "time": "10:00"},
            headers=headers_u1
        )
        assert res1.status_code == 201
        log1_id = res1.json()["id"]

        # User 2 logs 300 ml
        res2 = await client.post(
            "/api/water",
            json={"amount_ml": 300, "date": today_str, "time": "11:00"},
            headers=headers_u2
        )
        assert res2.status_code == 201

        # User 1 today summary should only contain User 1's entries
        res_u1 = await client.get(f"/api/water/today?date={today_str}", headers=headers_u1)
        assert res_u1.status_code == 200
        u1_logs = res_u1.json()["logs"]
        assert len(u1_logs) == 1
        assert u1_logs[0]["id"] == log1_id
        assert res_u1.json()["consumed_ml"] == 500.0

        # User 2 attempts to delete User 1's log -> 404 Not Found
        res_del_cross = await client.delete(f"/api/water/{log1_id}", headers=headers_u2)
        assert res_del_cross.status_code == 404

@pytest.mark.asyncio
async def test_water_daily_and_weekly_summary_integration():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await create_test_user(client, weight_kg=70.0)
        today_str = datetime.now(timezone.utc).date().isoformat()

        # Log 2000 ml for today
        res = await client.post(
            "/api/water",
            json={"amount_ml": 2000, "date": today_str, "time": "14:00"},
            headers=headers
        )
        assert res.status_code == 201

        # Check daily summary for today
        res_ds = await client.get(f"/api/daily-summary?date={today_str}", headers=headers)
        assert res_ds.status_code == 200
        ds_data = res_ds.json()
        assert ds_data["hydration"]["consumed_ml"] == 2000.0
        assert ds_data["hydration"]["target_ml"] == 2450.0  # 70 * 35

        # Check weekly summary for today
        res_ws = await client.get(f"/api/weekly-summary?date={today_str}", headers=headers)
        assert res_ws.status_code == 200
        ws_data = res_ws.json()
        assert ws_data["summary"]["total_water_ml"] >= 2000.0
        assert ws_data["summary"]["avg_water_ml"] > 0
