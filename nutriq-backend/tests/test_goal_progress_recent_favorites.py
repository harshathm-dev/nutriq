import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app

def make_test_user():
    uid = uuid.uuid4().hex[:8]
    return {
        "name": f"Goal User {uid}",
        "email": f"goal_user_{uid}@example.com",
        "password": "SecurePassword123!"
    }

@pytest.mark.asyncio
async def test_favorites_and_recent_foods_api_flow():
    user = make_test_user()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register user
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

        # 2. Setup Profile
        await client.post("/api/profile", headers=headers, json={
            "name": user["name"],
            "age": 28,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 85.0,
            "activity_level": "moderate",
            "fitness_goal": "weight_loss"
        })

        # 3. Search foods from catalog
        foods_res = await client.get("/api/foods?limit=5", headers=headers)
        assert foods_res.status_code == 200
        catalog_foods = foods_res.json()
        assert len(catalog_foods) >= 2
        food1 = catalog_foods[0]
        food2 = catalog_foods[1]

        # 4. Log a meal using food1
        meal_res = await client.post("/api/meals", headers=headers, json={
            "meal_type": "breakfast",
            "source": "manual",
            "items": [
                {
                    "food_id": food1["id"],
                    "food_name": food1["name"],
                    "quantity": 1.0,
                    "serving_unit": "serving",
                    "grams": 100.0,
                    "calories": food1["calories"],
                    "protein_g": food1["protein_g"],
                    "carbs_g": food1["carbs_g"],
                    "fat_g": food1["fat_g"]
                }
            ]
        })
        assert meal_res.status_code == 201

        # 5. Check Recent Foods endpoint
        recent_res = await client.get("/api/foods/recent", headers=headers)
        assert recent_res.status_code == 200
        recent = recent_res.json()
        assert len(recent) >= 1
        assert any(r["name"] == food1["name"] for r in recent)

        # 6. Add food2 to favorites
        fav_res = await client.post(f"/api/foods/{food2['id']}/favorite", headers=headers)
        assert fav_res.status_code == 200
        assert fav_res.json()["is_favorite"] is True

        # 7. List favorites
        fav_list_res = await client.get("/api/foods/favorites", headers=headers)
        assert fav_list_res.status_code == 200
        fav_list = fav_list_res.json()
        assert len(fav_list) >= 1
        assert any(f["id"] == food2["id"] for f in fav_list)

        # 8. Check that food search now tags is_favorite accurately
        catalog_search = await client.get(f"/api/foods/search?q={food2['name'][:6]}", headers=headers)
        assert catalog_search.status_code == 200
        matching = [f for f in catalog_search.json() if f["id"] == food2["id"]]
        if matching:
            assert matching[0]["is_favorite"] is True

        # 9. Remove from favorites
        del_fav = await client.delete(f"/api/foods/{food2['id']}/favorite", headers=headers)
        assert del_fav.status_code == 200
        assert del_fav.json()["is_favorite"] is False

        # 10. Verify favorites list is now empty of food2
        fav_list_after = await client.get("/api/foods/favorites", headers=headers)
        assert not any(f["id"] == food2["id"] for f in fav_list_after.json())


@pytest.mark.asyncio
async def test_goal_progress_weight_sync_and_safe_pace():
    user = make_test_user()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register user
        reg_res = await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Setup Profile & Initial Goal (85 kg -> 75 kg at 0.5 kg/week)
        await client.post("/api/profile", headers=headers, json={
            "name": user["name"],
            "age": 28,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 85.0,
            "activity_level": "moderate",
            "fitness_goal": "weight_loss"
        })

        await client.post("/api/goals", headers=headers, json={
            "goal_type": "weight_loss",
            "current_weight_kg": 85.0,
            "target_weight_kg": 75.0,
            "desired_rate": 0.5
        })

        # 3. Retrieve Goal Progress
        prog_res = await client.get("/api/goals/progress", headers=headers)
        assert prog_res.status_code == 200
        prog = prog_res.json()
        assert prog["starting_weight_kg"] == 85.0
        assert prog["current_weight_kg"] == 85.0
        assert prog["target_weight_kg"] == 75.0
        assert prog["weight_remaining_kg"] == 10.0
        assert prog["weekly_pace_kg"] == 0.5
        assert prog["is_pace_aggressive"] is False
        assert prog["estimated_weeks_remaining"] == 20.0
        assert prog["estimated_target_date"] is not None

        # 4. Log a new weight entry (Lost 3 kg: 85 -> 82 kg)
        wt_res = await client.post("/api/weight", json={"weight_kg": 82.0}, headers=headers)
        assert wt_res.status_code == 201

        # 5. Check updated progress calculation
        prog_res2 = await client.get("/api/goals/progress", headers=headers)
        assert prog_res2.status_code == 200
        prog2 = prog_res2.json()
        assert prog2["current_weight_kg"] == 82.0
        assert prog2["weight_lost_kg"] == 3.0
        assert prog2["weight_remaining_kg"] == 7.0
        assert prog2["progress_percentage"] == 30.0
        assert prog2["estimated_weeks_remaining"] == 14.0

        # 6. Test safe pace warning when user updates goal to aggressive pace (1.2 kg/wk)
        update_goal_res = await client.post("/api/goals", json={
            "goal_type": "weight_loss",
            "current_weight_kg": 82.0,
            "target_weight_kg": 75.0,
            "desired_rate": 1.2
        }, headers=headers)
        assert update_goal_res.status_code == 201

        prog_res3 = await client.get("/api/goals/progress", headers=headers)
        assert prog_res3.status_code == 200
        prog3 = prog_res3.json()
        assert prog3["weekly_pace_kg"] == 1.2
        assert prog3["is_pace_aggressive"] is True
        assert prog3["pace_warning_message"] is not None
        assert "aggressive" in prog3["pace_warning_message"].lower()
