import pytest
import uuid
import json
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app

def make_user():
    uid = uuid.uuid4().hex[:8]
    return {
        "name": f"Weekly User {uid}",
        "email": f"weekly_user_{uid}@example.com",
        "password": "SecurePassword123!"
    }

@pytest.mark.asyncio
async def test_weekly_summary_endpoint():
    """Test GET /api/weekly-summary aggregation and rule-based insights"""
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
            "weight_kg": 75.0,
            "activity_level": "moderately_active",
            "fitness_goal": "maintain",
            "dietary_preference": "standard"
        })

        # Fetch sample food
        food_res = await client.get("/api/foods?query=Dosa")
        food = food_res.json()[0]

        # Log meals across multiple days
        today = datetime.now(timezone.utc)
        for i in range(3):
            past_date = today - timedelta(days=i)
            iso_ts = past_date.isoformat()
            await client.post("/api/meals", headers=headers, json={
                "meal_type": "breakfast",
                "source": "manual",
                "occurred_at": iso_ts,
                "items": [{
                    "food_id": food["id"],
                    "food_name": food["name"],
                    "quantity": 2.0,
                    "serving_unit": "piece",
                    "grams": 200.0,
                    "calories": 268.0,
                    "protein_g": 6.0,
                    "carbs_g": 38.0,
                    "fat_g": 10.0,
                    "fiber_g": 2.0
                }]
            })

        # Test GET /api/weekly-summary
        weekly_res = await client.get("/api/weekly-summary", headers=headers)
        assert weekly_res.status_code == 200
        data = weekly_res.json()
        assert "summary" in data
        assert "daily_breakdown" in data
        assert len(data["daily_breakdown"]) == 7
        assert data["summary"]["total_weekly_calories"] > 0
        assert "insights" in data
        assert len(data["insights"]) > 0

@pytest.mark.asyncio
async def test_offline_sync_batch_processing():
    """Test POST /api/sync for offline batch sync and duplicate prevention"""
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
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Setup Profile
        await client.post("/api/profile", headers=headers, json={
            "name": user["name"],
            "age": 28,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 75.0,
            "activity_level": "moderately_active",
            "fitness_goal": "maintain",
            "dietary_preference": "standard"
        })

        # Sync offline meal & water
        client_ts = datetime.now(timezone.utc).isoformat()
        temp_meal_id = "offline_meal_" + uuid.uuid4().hex[:8]
        temp_water_id = "offline_water_" + uuid.uuid4().hex[:8]

        sync_payload = {
            "device_id": "test_device_browser_001",
            "changes": [
                {
                    "entity_type": "meal",
                    "entity_id": temp_meal_id,
                    "operation": "INSERT",
                    "client_timestamp": client_ts,
                    "payload": {
                        "meal_type": "lunch",
                        "items": [{
                            "food_id": "ifct_001",
                            "food_name": "Brown Rice & Dal",
                            "quantity": 1.0,
                            "serving_unit": "plate",
                            "grams": 250.0,
                            "calories": 340.0,
                            "protein_g": 14.0,
                            "carbs_g": 56.0,
                            "fat_g": 6.0,
                            "fiber_g": 7.0
                        }]
                    }
                },
                {
                    "entity_type": "water",
                    "entity_id": temp_water_id,
                    "operation": "INSERT",
                    "client_timestamp": client_ts,
                    "payload": {
                        "amount_ml": 500
                    }
                }
            ]
        }

        # 1. First sync -> processed
        sync_res = await client.post("/api/sync", headers=headers, json=sync_payload)
        assert sync_res.status_code == 200
        assert sync_res.json()["processed_count"] == 2

        # 2. Duplicate sync -> idempotently skipped (processed_count == 0)
        dup_sync_res = await client.post("/api/sync", headers=headers, json=sync_payload)
        assert dup_sync_res.status_code == 200
        assert dup_sync_res.json()["processed_count"] == 0

        # Verify meal exists in user's meals
        meals_res = await client.get("/api/meals", headers=headers)
        assert meals_res.status_code == 200
        assert any(m["id"] == temp_meal_id for m in meals_res.json())
