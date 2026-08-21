import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.nutrition_engine import NutritionEngine

def make_user(prefix="cal_user"):
    uid = uuid.uuid4().hex[:8]
    return {
        "name": f"User {prefix} {uid}",
        "email": f"{prefix}_{uid}@example.com",
        "password": "SecurePassword123!"
    }

def test_unit_nutrition_engine_calculate_calorie_status():
    """Unit test for NutritionEngine.calculate_calorie_status across all 7 prompt cases"""
    target = 2294.0

    # Case 1: Target = 2,294, Consumed = 1,218, Exercise = 756
    # 1218 / 2294 = 53.1% -> below_target
    res1 = NutritionEngine.calculate_calorie_status(
        target_calories=target,
        consumed_calories=1218.0,
        burned_calories=756.0,
        fitness_goal="weight_loss",
        has_meals=True
    )
    assert res1["status"] == "below_target"
    assert res1["status_badge"] == "Below Today's Target"
    assert res1["consumed"] == 1218.0
    assert res1["target"] == 2294.0
    assert res1["remaining"] == 1076.0
    assert res1["burned"] == 756.0
    assert res1["net_energy_after_exercise"] == 462.0
    assert "1,218" in res1["message"]
    assert "2,294" in res1["message"]
    assert "1,076" in res1["message"]
    assert "756" in res1["message"]

    # Case 2: Target = 2,294, Consumed = 2,100, Exercise = 300
    # 2100 / 2294 = 91.5% -> on_track
    res2 = NutritionEngine.calculate_calorie_status(
        target_calories=target,
        consumed_calories=2100.0,
        burned_calories=300.0,
        fitness_goal="weight_loss",
        has_meals=True
    )
    assert res2["status"] == "on_track"
    assert res2["status_badge"] == "On Track"
    assert res2["consumed"] == 2100.0
    assert res2["remaining"] == 194.0

    # Case 3: Target = 2,294, Consumed = 2,500, Exercise = 300
    # 2500 > 2294 + 50 -> target_exceeded
    res3 = NutritionEngine.calculate_calorie_status(
        target_calories=target,
        consumed_calories=2500.0,
        burned_calories=300.0,
        fitness_goal="weight_loss",
        has_meals=True
    )
    assert res3["status"] == "target_exceeded"
    assert res3["status_badge"] == "Target Exceeded"
    assert res3["surplus"] == 206.0
    assert "exceeded" in res3["message"].lower()

    # Case 4: Target = 2,294, Consumed = 400 (very low amount < 50%)
    res4 = NutritionEngine.calculate_calorie_status(
        target_calories=target,
        consumed_calories=400.0,
        burned_calories=0.0,
        fitness_goal="weight_loss",
        has_meals=True
    )
    assert res4["status"] == "very_low"
    assert res4["status_badge"] == "Very Low Intake"
    assert "unusually low" in res4["message"].lower()

    # Case 5: No meals logged
    res5 = NutritionEngine.calculate_calorie_status(
        target_calories=target,
        consumed_calories=0.0,
        burned_calories=0.0,
        fitness_goal="weight_loss",
        has_meals=False
    )
    assert res5["status"] == "no_meals"
    assert res5["status_badge"] == "No Meals Logged Yet"
    assert "no meals logged yet" in res5["message"].lower()

    # Case 6: Meals logged but no exercise (Target = 2294, Consumed = 1218, Burned = 0)
    res6 = NutritionEngine.calculate_calorie_status(
        target_calories=target,
        consumed_calories=1218.0,
        burned_calories=0.0,
        fitness_goal="weight_loss",
        has_meals=True
    )
    assert res6["status"] == "below_target"
    assert res6["burned"] == 0.0
    assert "physical activity" not in res6["message"].lower()

    # Case 7: Exercise logged but no meals (Target = 2294, Consumed = 0, Burned = 756)
    res7 = NutritionEngine.calculate_calorie_status(
        target_calories=target,
        consumed_calories=0.0,
        burned_calories=756.0,
        fitness_goal="weight_loss",
        has_meals=False
    )
    assert res7["status"] == "no_meals"
    assert res7["consumed"] == 0.0
    assert res7["burned"] == 756.0
    assert res7["net_energy_after_exercise"] == -756.0
    assert "logged 756 kcal of physical activity" in res7["message"].lower()

@pytest.mark.asyncio
async def test_api_calorie_status_and_daily_summary_workflow():
    """End-to-end API test verifying Calorie Status and Daily Summary endpoints"""
    user = make_user("api_status")
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
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Setup Profile for Weight Loss with ~2294 target
        # Male 28y, 180cm, 85kg, moderately_active (1.55) -> BMR ~1840, TDEE ~2852 - 550 = ~2302 kcal
        await client.post("/api/profile", headers=headers, json={
            "name": user["name"],
            "age": 28,
            "gender": "male",
            "height_cm": 180.0,
            "weight_kg": 85.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "vegetarian"
        })

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 1. No meals logged: Check Status and Daily Summary
        res = await client.get(f"/api/daily-summary?date={today_str}", headers=headers)
        assert res.status_code == 200
        ds = res.json()
        assert ds["goal_status"] == "No Meals Logged Yet"
        assert ds["calories"]["consumed"] == 0.0

        # 2. Log 756 kcal exercise (Gym workout)
        await client.post("/api/activities", headers=headers, json={
            "activity_type": "gym_workout",
            "duration_minutes": 90,
            "intensity": "high",
            "calories_burned": 756.0,
            "date": today_str
        })

        # 3. Log 1218 kcal of food (Idli & Sambar + Lunch)
        await client.post("/api/meals", headers=headers, json={
            "meal_type": "breakfast",
            "date": today_str,
            "items": [{
                "food_id": "f_1",
                "food_name": "Idli with Sambar",
                "quantity": 3.0,
                "serving_unit": "piece",
                "grams": 240.0,
                "calories": 418.0,
                "protein_g": 12.0,
                "carbs_g": 70.0,
                "fat_g": 5.0,
                "fiber_g": 6.0
            }]
        })
        await client.post("/api/meals", headers=headers, json={
            "meal_type": "lunch",
            "date": today_str,
            "items": [{
                "food_id": "f_2",
                "food_name": "Vegetable Biryani with Raita",
                "quantity": 1.0,
                "serving_unit": "plate",
                "grams": 350.0,
                "calories": 800.0,
                "protein_g": 16.0,
                "carbs_g": 110.0,
                "fat_g": 20.0,
                "fiber_g": 8.0
            }]
        })

        # 4. Verify Daily Summary: Food consumed = 1218 kcal, Burned = 756 kcal
        res = await client.get(f"/api/daily-summary?date={today_str}", headers=headers)
        assert res.status_code == 200
        ds = res.json()
        assert ds["calories"]["consumed"] == 1218.0
        assert ds["calories"]["burned"] == 756.0
        assert ds["calories"]["net"] == 462.0
        assert ds["goal_status"] == "Below Today's Target"
        assert "1,218" in ds["daily_insight"]
        assert "756" in ds["daily_insight"]

        # 5. Verify /api/nutrition/status returns separate food consumed, target, and exercise
        status_res = await client.get(f"/api/nutrition/status?date={today_str}", headers=headers)
        assert status_res.status_code == 200
        ns = status_res.json()
        assert ns["calories_consumed"] == 1218.0
        assert ns["calories_burned"] == 756.0
        assert ns["net_energy_after_exercise"] == 462.0
        assert ns["status_badge"] == "Below Today's Target"
        assert ns["status_level"] == "below_target"
