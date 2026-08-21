import pytest
from app.services.nutrition_engine import NutritionEngine

def test_mifflin_st_jeor_male():
    # Men: (10 * 70) + (6.25 * 175) - (5 * 25) + 5
    # 700 + 1093.75 - 125 + 5 = 1673.75
    bmr = NutritionEngine.calculate_bmr(weight_kg=70.0, height_cm=175.0, age=25, gender="male")
    assert bmr == 1673.75

def test_mifflin_st_jeor_female():
    # Women: (10 * 60) + (6.25 * 160) - (5 * 30) - 161
    # 600 + 1000 - 150 - 161 = 1289.0
    bmr = NutritionEngine.calculate_bmr(weight_kg=60.0, height_cm=160.0, age=30, gender="female")
    assert bmr == 1289.0

def test_tdee_calculation():
    bmr = 1600.0
    tdee = NutritionEngine.calculate_tdee(bmr, "moderately_active")
    assert tdee == round(1600.0 * 1.55, 2)

def test_safe_minimum_calorie_floor():
    # Extreme deficit for small female should be clamped to SAFE_MIN_CALORIES (1200)
    targets = NutritionEngine.calculate_targets(
        weight_kg=45.0,
        height_cm=145.0,
        age=50,
        gender="female",
        activity_level="sedentary",
        fitness_goal="weight_loss",
        desired_rate=1.5
    )
    assert targets["target_calories"] >= 1200.0
    assert targets["safe_floor_applied"] == True

def test_protein_and_macro_splits():
    targets = NutritionEngine.calculate_targets(
        weight_kg=80.0,
        height_cm=180.0,
        age=28,
        gender="male",
        activity_level="very_active",
        fitness_goal="muscle_building"
    )
    assert targets["protein_g"] >= 120.0
    assert targets["fiber_g"] > 20.0
    assert targets["water_ml"] == 2800.0
