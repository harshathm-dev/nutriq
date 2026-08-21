import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone, date
from app.main import app
from app.services.nutrition_engine import NutritionEngine
from app.services.food_service import FoodService
from app.services.agent_service import MealPlanningAgent
from app.utils.date_utils import get_today_local

@pytest.fixture
def unique_email():
    return f"stability_{uuid.uuid4().hex[:8]}@example.com"

@pytest.mark.asyncio
async def test_mifflin_st_jeor_engine_zero_ai_dependency():
    """Verify deterministic Mifflin-St Jeor formulas operate 100% without AI."""
    # Male test: 80kg, 180cm, 30yo
    # BMR = (10*80) + (6.25*180) - (5*30) + 5 = 800 + 1125 - 150 + 5 = 1780.0
    bmr_m = NutritionEngine.calculate_bmr(weight_kg=80.0, height_cm=180.0, age=30, gender="male")
    assert bmr_m == 1780.0

    # Female test: 60kg, 165cm, 28yo
    # BMR = (10*60) + (6.25*165) - (5*28) - 161 = 600 + 1031.25 - 140 - 161 = 1330.25
    bmr_f = NutritionEngine.calculate_bmr(weight_kg=60.0, height_cm=165.0, age=28, gender="female")
    assert bmr_f == 1330.25

    # TDEE moderately active (x 1.55)
    tdee_m = NutritionEngine.calculate_tdee(bmr=bmr_m, activity_level="moderately_active")
    assert tdee_m == round(1780.0 * 1.55, 2)

    # Full targets calculation
    targets = NutritionEngine.calculate_targets(
        weight_kg=75.0,
        height_cm=175.0,
        age=25,
        gender="male",
        activity_level="moderately_active",
        fitness_goal="weight_loss",
        desired_rate=0.5,
        dietary_preference="standard"
    )
    assert "target_calories" in targets
    assert "protein_g" in targets
    assert "carbs_g" in targets
    assert "fat_g" in targets
    assert targets["target_calories"] >= 1200.0

@pytest.mark.asyncio
async def test_food_catalog_and_quantity_multipliers():
    """Verify food search and per-unit quantity multipliers (e.g. 1 vs 2 vs 3 Dosa)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Search food
        res = await ac.get("/api/foods?query=dosa")
        assert res.status_code == 200
        foods = res.json()
        assert len(foods) > 0
        
        plain_dosa = next((f for f in foods if "Plain Dosa" in f["name"]), foods[0])
        base_cal_100g = plain_dosa["calories"]
        base_pro_100g = plain_dosa["protein_g"]
        
        # Test 1 Dosa (80g) vs 2 Dosa (160g) vs 3 Dosa (240g)
        serving_grams = 80.0
        
        # 1 dosa
        cal_1 = round(base_cal_100g * (serving_grams * 1 / 100.0))
        pro_1 = round(base_pro_100g * (serving_grams * 1 / 100.0), 1)
        
        # 2 dosas
        cal_2 = round(base_cal_100g * (serving_grams * 2 / 100.0))
        pro_2 = round(base_pro_100g * (serving_grams * 2 / 100.0), 1)
        
        # 3 dosas
        cal_3 = round(base_cal_100g * (serving_grams * 3 / 100.0))
        pro_3 = round(base_pro_100g * (serving_grams * 3 / 100.0), 1)
        
        assert cal_2 == pytest.approx(cal_1 * 2, abs=1)
        assert cal_3 == pytest.approx(cal_1 * 3, abs=2)
        assert pro_2 == pytest.approx(pro_1 * 2, abs=0.2)
        assert pro_3 == pytest.approx(pro_1 * 3, abs=0.3)

@pytest.mark.asyncio
async def test_full_auth_profile_meal_logging_flow(unique_email):
    """Verify complete logging, daily summary, and export flow works without AI."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register
        reg_res = await ac.post("/api/auth/register", json={
            "email": unique_email,
            "password": "Password123!",
            "name": "Karthik Raja"
        })
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Setup Profile
        prof_res = await ac.put("/api/profile", headers=headers, json={
            "name": "Karthik Raja",
            "age": 28,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 72.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "non_vegetarian",
            "food_preferences": "South Indian"
        })
        assert prof_res.status_code == 200
        prof = prof_res.json()
        assert prof["weight_kg"] == 72.0

        # 3. Log a Breakfast Meal (2 Idlis + Sambar)
        meal_res = await ac.post("/api/meals", headers=headers, json={
            "meal_type": "breakfast",
            "source": "search",
            "items": [
                {
                    "food_name": "Idli (Steamed Rice Cake)",
                    "quantity": 2,
                    "serving_unit": "piece",
                    "grams": 90.0,
                    "calories": 126.0,
                    "protein_g": 3.8,
                    "carbs_g": 26.1,
                    "fat_g": 0.4,
                    "fiber_g": 1.4,
                    "sugar_g": 0.2,
                    "sodium_mg": 162.0
                },
                {
                    "food_name": "Tamil Tiffin Sambar",
                    "quantity": 1,
                    "serving_unit": "katori",
                    "grams": 150.0,
                    "calories": 105.0,
                    "protein_g": 4.5,
                    "carbs_g": 15.0,
                    "fat_g": 3.0,
                    "fiber_g": 3.2,
                    "sugar_g": 1.5,
                    "sodium_mg": 380.0
                }
            ]
        })
        assert meal_res.status_code == 201
        logged_meal = meal_res.json()
        assert len(logged_meal["items"]) == 2
        assert logged_meal["totals"]["calories"] == 231.0

        # 4. Check Daily Summary
        today_str = get_today_local().isoformat()
        summary_res = await ac.get(f"/api/daily-summary?date={today_str}", headers=headers)
        assert summary_res.status_code == 200
        summary = summary_res.json()
        assert summary["date"] == today_str
        assert summary["calories"]["consumed"] == 231.0
        assert summary["macros"]["protein"]["consumed"] == 8.3
        assert "goal_status" in summary

        # 5. Check Smart Meal Reminders
        reminders_res = await ac.get("/api/reminders/pending", headers=headers)
        assert reminders_res.status_code == 200

        # 6. Check Weekly Analytics
        analytics_res = await ac.get("/api/analytics/weekly", headers=headers)
        assert analytics_res.status_code == 200
        analytics = analytics_res.json()
        assert analytics["has_data"] is True
        assert len(analytics["daily_breakdown"]) == 7

        # 7. Check Data Exports (PDF, CSV, JSON)
        json_exp = await ac.get("/api/export/json", headers=headers)
        assert json_exp.status_code == 200
        json_data = json_exp.json()
        assert len(json_data["meals"]) >= 1

        csv_exp = await ac.get("/api/export/csv", headers=headers)
        assert csv_exp.status_code == 200
        assert "Idli" in csv_exp.text

        pdf_exp = await ac.get("/api/export/pdf", headers=headers)
        assert pdf_exp.status_code == 200
        assert pdf_exp.headers.get("content-type") == "application/pdf"

@pytest.mark.asyncio
async def test_deterministic_7day_meal_planner_variety():
    """Verify MealPlanningAgent generates 7 varied, non-repeating days with Indian foods."""
    planner = MealPlanningAgent()
    plan = planner.run(
        target_calories=2000.0,
        dietary_pref="non_vegetarian",
        days=7,
        user_name="Karthik",
        allergies=[]
    )
    
    assert plan["daily_target_calories"] == 2000.0
    days = plan["days"]
    assert len(days) == 7

    # Check distinct breakfasts across days
    mon_b = days["Monday"]["breakfast"]["name"]
    tue_b = days["Tuesday"]["breakfast"]["name"]
    wed_b = days["Wednesday"]["breakfast"]["name"]
    assert mon_b != tue_b
    assert tue_b != wed_b

    # Check each day has calibrated calorie summary
    for day_name, day_info in days.items():
        assert "daily_summary" in day_info
        assert day_info["daily_summary"]["total_calories"] == pytest.approx(2000, abs=50)

@pytest.mark.asyncio
async def test_ai_assistant_graceful_unavailable_fallback(unique_email):
    """Verify AI Assistant endpoints return clean fallback message when offline."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register user
        reg_res = await ac.post("/api/auth/register", json={
            "email": unique_email,
            "password": "Password123!",
            "name": "Arun Kumar"
        })
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Query chat assistant
        chat_res = await ac.post("/api/ai/chat", headers=headers, json={
            "messages": [{"role": "user", "content": "How many calories do I have left?"}]
        })
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        assert "response" in chat_data
        assert len(chat_data["response"]) > 0

        # Query recommendation endpoint
        rec_res = await ac.post("/api/ai/recommend", headers=headers)
        assert rec_res.status_code == 200
        recs = rec_res.json()
        assert isinstance(recs, list)
