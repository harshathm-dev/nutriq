import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app

def make_user(prefix="rec"):
    uid = uuid.uuid4().hex[:8]
    return {
        "name": f"Test {prefix} {uid}",
        "email": f"{prefix}_{uid}@example.com",
        "password": "SecurePassword123!"
    }

@pytest.mark.asyncio
async def test_get_smart_recommendations_endpoint():
    user = make_user("smart_rec")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register
        reg = await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg.status_code in [200, 201], reg.text
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Profile Setup
        await client.post("/api/profile", headers=headers, json={
            "name": user["name"],
            "age": 28,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 75.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "vegetarian"
        })

        # 3. GET /api/recommendations
        res = await client.get("/api/recommendations?date=2026-08-20&meal_type=breakfast&limit=4", headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()

        assert "recommendations" in data
        assert "remaining_needs" in data
        assert "gaps" in data
        assert len(data["recommendations"]) <= 4
        assert len(data["recommendations"]) > 0

        first_rec = data["recommendations"][0]
        assert "food_name" in first_rec
        assert "calories" in first_rec
        assert "protein_g" in first_rec
        assert "reason" in first_rec
        assert "suitability_score" in first_rec
        assert first_rec["calories"] > 0

        # 4. POST /api/recommendations
        post_res = await client.post("/api/recommendations", headers=headers, json={
            "date": "2026-08-20",
            "meal_type": "lunch",
            "limit": 3
        })
        assert post_res.status_code == 200, post_res.text
        post_data = post_res.json()
        assert len(post_data["recommendations"]) <= 3
        assert post_data["remaining_needs"]["calories"] >= 0

@pytest.mark.asyncio
async def test_smart_recommendation_dietary_safety():
    user = make_user("safety")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register
        reg = await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Vegetarian Profile
        await client.post("/api/profile", headers=headers, json={
            "name": user["name"],
            "age": 30,
            "gender": "female",
            "height_cm": 160.0,
            "weight_kg": 60.0,
            "activity_level": "lightly_active",
            "fitness_goal": "maintain",
            "dietary_preference": "vegetarian"
        })

        # Test dietary safety filter: verify no non-veg items returned
        res = await client.get("/api/recommendations?date=2026-08-20&meal_type=dinner&limit=6", headers=headers)
        assert res.status_code == 200
        data = res.json()

        non_veg_keywords = ["chicken", "mutton", "fish", "prawn", "beef", "pork"]
        for rec in data["recommendations"]:
            name_lower = rec["food_name"].lower()
            for kw in non_veg_keywords:
                assert kw not in name_lower, f"Vegetarian safety filter failed: {rec['food_name']} contains {kw}"
