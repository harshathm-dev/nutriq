import pytest
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app

def make_user(prefix="user"):
    uid = uuid.uuid4().hex[:8]
    return {
        "name": f"Test {prefix} {uid}",
        "email": f"{prefix}_{uid}@example.com",
        "password": "SecurePassword123!"
    }

@pytest.mark.asyncio
async def test_weight_loss_warnings_and_levels():
    """Test 1, 2, 3: Weight Loss user on-track, slightly above, and significantly above target"""
    user = make_user("wl")
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

        # Profile: Weight Loss target ~1800 kcal
        await client.post("/api/profile", headers=headers, json={
            "name": user["name"],
            "age": 28,
            "gender": "female",
            "height_cm": 165.0,
            "weight_kg": 68.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "vegetarian"
        })

        # Check initial status (No meals)
        res1 = await client.get("/api/nutrition/status", headers=headers)
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status_level"] in ["no_meals", "on_track"]
        target_cal = data1["daily_calorie_target"]

        # 1. Log a light meal (280 kcal) -> Below target / very low intake
        await client.post("/api/meals", headers=headers, json={
            "meal_type": "breakfast",
            "items": [{
                "food_id": "item_1",
                "food_name": "Idli with Sambar",
                "quantity": 2.0,
                "serving_unit": "piece",
                "grams": 160.0,
                "calories": 280.0,
                "protein_g": 8.0,
                "carbs_g": 48.0,
                "fat_g": 3.0,
                "fiber_g": 4.0
            }]
        })

        res2 = await client.get("/api/nutrition/status", headers=headers)
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["status_level"] in ["below_target", "very_low", "on_track"]
        assert data2["calories_remaining"] > 0

        # 2. Log second meal bringing calories to target + 120 kcal -> Target Exceeded / Above target
        excess_cal = (target_cal - 280.0) + 120.0
        await client.post("/api/meals", headers=headers, json={
            "meal_type": "lunch",
            "items": [{
                "food_id": "item_2",
                "food_name": "Vegetable Thali",
                "quantity": 1.0,
                "serving_unit": "thali",
                "grams": 450.0,
                "calories": excess_cal,
                "protein_g": 20.0,
                "carbs_g": 120.0,
                "fat_g": 25.0,
                "fiber_g": 10.0
            }]
        })

        res3 = await client.get("/api/nutrition/status", headers=headers)
        assert res3.status_code == 200
        data3 = res3.json()
        assert data3["status_level"] in ["slightly_above", "target_exceeded"]
        assert "target" in data3["warning_message"].lower() or "exceeded" in data3["warning_message"].lower()

        # 3. Log a heavy dinner adding +350 kcal -> Target Exceeded
        await client.post("/api/meals", headers=headers, json={
            "meal_type": "dinner",
            "items": [{
                "food_id": "item_3",
                "food_name": "Paneer Butter Masala with Naan",
                "quantity": 1.0,
                "serving_unit": "portion",
                "grams": 300.0,
                "calories": 400.0,
                "protein_g": 14.0,
                "carbs_g": 40.0,
                "fat_g": 22.0,
                "fiber_g": 3.0
            }]
        })

        res4 = await client.get("/api/nutrition/status", headers=headers)
        assert res4.status_code == 200
        data4 = res4.json()
        assert data4["status_level"] in ["significantly_above", "target_exceeded"]
        assert len(data4["recommendations"]) > 0
        # Recommendations should be light
        for rec in data4["recommendations"]:
            assert rec["calories"] <= 250.0

@pytest.mark.asyncio
async def test_muscle_gain_low_protein_warning():
    """Test 6: Muscle Gain user with low protein triggers protein warning"""
    user = make_user("muscle")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Profile: Muscle Gain
        await client.post("/api/profile", headers=headers, json={
            "name": user["name"],
            "age": 25,
            "gender": "male",
            "height_cm": 180.0,
            "weight_kg": 80.0,
            "activity_level": "very_active",
            "fitness_goal": "muscle_building",
            "dietary_preference": "standard"
        })

        # Log meals with plenty of calories but low protein (e.g. 1500 kcal, only 15g protein)
        await client.post("/api/meals", headers=headers, json={
            "meal_type": "lunch",
            "items": [{
                "food_id": "carby_item",
                "food_name": "White Rice with Butter and Potato Fry",
                "quantity": 2.0,
                "serving_unit": "plate",
                "grams": 600.0,
                "calories": 1600.0,
                "protein_g": 12.0,
                "carbs_g": 240.0,
                "fat_g": 50.0,
                "fiber_g": 4.0
            }]
        })

        res = await client.get("/api/nutrition/status", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status_level"] in ["protein_low", "below_target", "very_low"] or data.get("protein_status") == "below_target"
        # Recommendations should include high-protein choices
        recs = data["recommendations"]
        assert len(recs) > 0
        assert any(r["protein_g"] >= 6.0 for r in recs)

@pytest.mark.asyncio
async def test_allergy_and_vegetarian_safety():
    """Test 7 & 8: Vegetarian and Dairy-Allergic user never receives meat or dairy recommendations"""
    user = make_user("allergy")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
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
            "weight_kg": 58.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "vegetarian"
        })

        # Add Dairy Allergy
        await client.post("/api/allergies", headers=headers, json={
            "allergen_type": "Dairy / Lactose",
            "severity": "severe",
            "notes": "Severe lactose intolerance"
        })

        res = await client.get("/api/nutrition/status", headers=headers)
        assert res.status_code == 200
        recs = res.json()["recommendations"]

        dairy_and_meat = ["chicken", "mutton", "fish", "egg", "curd", "paneer", "milk", "butter", "cheese", "ghee", "yogurt"]
        for r in recs:
            name_lower = r["food_name"].lower()
            for bad_word in dairy_and_meat:
                assert bad_word not in name_lower, f"Forbidden allergen/meat '{bad_word}' found in recommendation: {r['food_name']}"

@pytest.mark.asyncio
async def test_maintenance_and_weight_gain_goals():
    """Test 4 & 5: Weight Maintenance and Weight Gain goals"""
    user = make_user("maint_gain")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Maintenance profile
        await client.post("/api/profile", headers=headers, json={
            "name": user["name"],
            "age": 27,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 72.0,
            "activity_level": "moderately_active",
            "fitness_goal": "maintain",
            "dietary_preference": "standard"
        })

        # Log excess calories (+250 kcal over target)
        res_maint_before = await client.get("/api/nutrition/status", headers=headers)
        t_cal = res_maint_before.json()["daily_calorie_target"]
        
        await client.post("/api/meals", headers=headers, json={
            "meal_type": "lunch",
            "items": [{
                "food_id": "m1",
                "food_name": "Heavy Feast",
                "quantity": 1.0,
                "serving_unit": "plate",
                "grams": 500.0,
                "calories": t_cal + 200.0,
                "protein_g": 30.0,
                "carbs_g": 180.0,
                "fat_g": 30.0,
                "fiber_g": 8.0
            }]
        })

        res_maint = await client.get("/api/nutrition/status", headers=headers)
        assert res_maint.status_code == 200
        assert res_maint.json()["status_level"] in ["slightly_above", "target_exceeded"]
        assert "maintenance" in res_maint.json()["warning_message"].lower() or "target" in res_maint.json()["warning_message"].lower()

        # 2. Update to Weight Gain profile
        await client.post("/api/profile", headers=headers, json={
            "name": user["name"],
            "age": 27,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 65.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_gain",
            "dietary_preference": "standard"
        })

        # On a fresh date with no meals logged yet, check below target status
        past_date = (datetime.now(timezone.utc) - timedelta(days=2)).date().isoformat()
        res_gain = await client.get(f"/api/nutrition/status?date={past_date}", headers=headers)
        assert res_gain.status_code == 200
        assert res_gain.json()["goal"] == "weight_gain"

@pytest.mark.asyncio
async def test_weekly_repeated_excess_pattern():
    """Test 12: Weekly repeated calorie excess triggers weekly pattern warning"""
    user = make_user("pattern")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await client.post("/api/profile", headers=headers, json={
            "name": user["name"],
            "age": 26,
            "gender": "female",
            "height_cm": 162.0,
            "weight_kg": 64.0,
            "activity_level": "lightly_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "standard"
        })

        # Log high calories across 3 past days
        today = datetime.now(timezone.utc)
        for offset in range(1, 4):
            past_iso = (today - timedelta(days=offset)).isoformat()
            await client.post("/api/meals", headers=headers, json={
                "meal_type": "dinner",
                "occurred_at": past_iso,
                "items": [{
                    "food_id": f"p_food_{offset}",
                    "food_name": "Biryani with Dessert",
                    "quantity": 1.0,
                    "serving_unit": "portion",
                    "grams": 500.0,
                    "calories": 2600.0,
                    "protein_g": 35.0,
                    "carbs_g": 200.0,
                    "fat_g": 45.0,
                    "fiber_g": 5.0
                }]
            })

        # Check today's status
        res = await client.get("/api/nutrition/status", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["weekly_pattern_warning"] is not None
        assert "several days" in data["weekly_pattern_warning"].lower() or "3 days" in data["weekly_pattern_warning"].lower()

