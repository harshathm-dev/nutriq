import pytest
from app.services.agent_service import MealPlanningAgent
from app.services.ai_service import AIService
from app.services.meal_service import MealService
from app.schemas.meal import MealCreate, MealItemCreate
from app.services.nutrition_engine import NutritionEngine

def test_dynamic_meal_planning_agent():
    planner = MealPlanningAgent()
    plan = planner.run(
        target_calories=2200.0,
        dietary_pref="vegetarian",
        days=7,
        user_name="Harshath",
        allergies=["peanuts", "dairy"]
    )

    assert plan["daily_target_calories"] == 2200.0
    assert len(plan["days"]) == 7

    # Check distinct day meals
    mon = plan["days"]["Monday"]
    tue = plan["days"]["Tuesday"]
    assert mon["breakfast"]["name"] != tue["breakfast"]["name"]
    
    # Check peanut & dairy replacements
    for day_name, day_plan in plan["days"].items():
        summary = day_plan["daily_summary"]
        assert summary["total_calories"] > 1800
        assert summary["total_protein_g"] > 0
        assert "peanuts" not in day_plan["breakfast"]["name"].lower()

def test_ai_intent_detection():
    intents = [
        ("how many calories do I have left today?", "calorie_status"),
        ("suggest a high protein dinner for tonight", "high_protein_request"),
        ("what should I eat for breakfast?", "meal_suggestion"),
        ("I ate 2 masala dosas with sambar", "food_logging"),
        ("replace white rice with something lower in calories", "food_substitution"),
        ("what did I eat today?", "meal_history_query"),
        ("how much water have I logged?", "water_query")
    ]
    for msg, expected_intent in intents:
        assert AIService.detect_intent(msg) == expected_intent

def test_mifflin_st_jeor_calculation():
    targets = NutritionEngine.calculate_targets(
        weight_kg=75.0,
        height_cm=180.0,
        age=28,
        gender="male",
        activity_level="moderately_active",
        fitness_goal="weight_loss",
        desired_rate=0.5,
        dietary_preference="standard"
    )
    # BMR = 10*75 + 6.25*180 - 5*28 + 5 = 750 + 1125 - 140 + 5 = 1740
    # TDEE = 1740 * 1.55 = 2697
    # Deficit = 0.5 * 7700 / 7 = 550
    # Target = 2697 - 550 = 2147
    assert targets["bmr"] == 1740.0
    assert targets["tdee"] == 2697.0
    assert targets["target_calories"] == 2147.0
    assert targets["protein_g"] > 100
