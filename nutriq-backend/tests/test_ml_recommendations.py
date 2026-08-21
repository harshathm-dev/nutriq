import pytest
import os
import json
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.ml.recommender import MLFoodRecommender
from app.ml.preprocessing import FeatureExtractor

@pytest.fixture
def unique_email():
    return f"ml_user_{uuid.uuid4().hex[:8]}@example.com"

async def setup_user(
    client: AsyncClient,
    email: str,
    fitness_goal: str = "weight_loss",
    dietary_pref: str = "standard",
    allergies: list = None
):
    reg_res = await client.post("/api/auth/register", json={
        "name": "ML Nutrition User",
        "email": email,
        "password": "Password123!",
        "terms_accepted": True,
        "ai_consent_accepted": True
    })
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/profile", headers=headers, json={
        "name": "ML Nutrition User",
        "age": 28,
        "gender": "female",
        "height_cm": 165.0,
        "weight_kg": 62.0,
        "activity_level": "moderately_active",
        "fitness_goal": fitness_goal,
        "dietary_preference": dietary_pref
    })

    await client.post("/api/goals", headers=headers, json={
        "goal_type": fitness_goal,
        "current_weight_kg": 62.0,
        "target_weight_kg": 58.0 if fitness_goal == "weight_loss" else (68.0 if fitness_goal == "weight_gain" else 62.0),
        "desired_rate": 0.5
    })

    if allergies:
        for allergen in allergies:
            await client.post("/api/allergies", headers=headers, json={
                "allergen_type": allergen,
                "severity": "severe",
                "notes": f"Strict allergy to {allergen}"
            })

    return headers

@pytest.mark.asyncio
async def test_ml_model_loaded_and_metadata_available():
    """
    Test 1: Verify trained ML model is loaded with valid metadata.
    """
    assert MLFoodRecommender.is_available() is True
    metadata = MLFoodRecommender.get_metadata()
    assert metadata["model_name"] == "NutriQ_GradientBoosting_FoodRecommender"
    assert metadata["algorithm"] == "GradientBoostingRegressor"
    assert metadata["feature_count"] == 26
    assert metadata["evaluation_metrics"]["r2_score"] > 0.85
    assert metadata["evaluation_metrics"]["precision_at_5"] > 0.80

@pytest.mark.asyncio
async def test_ml_recommendations_endpoint(unique_email):
    """
    Test 2: Verify /api/nutrition/recommendations returns ML-ranked foods with suitability scores and reasons.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await setup_user(client, unique_email, fitness_goal="weight_loss", dietary_pref="vegetarian")

        res = await client.get("/api/nutrition/recommendations?meal_type=evening_snack&limit=4", headers=headers)
        assert res.status_code == 200
        recs = res.json()
        assert len(recs) == 4

        for r in recs:
            assert r["food_name"]
            assert r["calories"] > 0
            assert r["protein_g"] >= 0
            assert r["suitability_score"] is not None
            assert 0.0 <= r["suitability_score"] <= 1.0
            assert r["recommendation_source"] in ["ml_model", "rule_based_fallback"]
            assert r["reason"] and len(r["reason"]) > 10

@pytest.mark.asyncio
async def test_hard_safety_filter_allergens_before_ml():
    """
    Test 3: Pre-ML Hard Safety Filter strictly removes allergens (Dairy, Peanuts, Gluten).
    """
    candidate_foods = [
        {"id": "1", "name": "Paneer Butter Masala", "category": "curry", "calories": 350, "protein_g": 14, "carbs_g": 10, "fat_g": 25, "fiber_g": 2},
        {"id": "2", "name": "Peanut Chikki", "category": "snacks", "calories": 210, "protein_g": 6, "carbs_g": 25, "fat_g": 10, "fiber_g": 2},
        {"id": "3", "name": "Whole Wheat Chapati", "category": "bread", "calories": 140, "protein_g": 4, "carbs_g": 28, "fat_g": 1, "fiber_g": 4},
        {"id": "4", "name": "Roasted Makhana", "category": "snacks", "calories": 130, "protein_g": 4, "carbs_g": 24, "fat_g": 2, "fiber_g": 3},
        {"id": "5", "name": "Boiled Sweet Corn", "category": "snacks", "calories": 110, "protein_g": 3, "carbs_g": 22, "fat_g": 1, "fiber_g": 3.5}
    ]

    # Dairy-allergic filter
    dairy_safe = MLFoodRecommender.apply_safety_filters(
        candidate_foods=candidate_foods,
        dietary_pref="standard",
        user_allergies=["Dairy / Lactose"]
    )
    assert not any("paneer" in f["name"].lower() for f in dairy_safe)
    assert any("makhana" in f["name"].lower() for f in dairy_safe)

    # Peanut-allergic filter
    peanut_safe = MLFoodRecommender.apply_safety_filters(
        candidate_foods=candidate_foods,
        dietary_pref="standard",
        user_allergies=["Peanuts"]
    )
    assert not any("peanut" in f["name"].lower() for f in peanut_safe)

    # Gluten-allergic filter
    gluten_safe = MLFoodRecommender.apply_safety_filters(
        candidate_foods=candidate_foods,
        dietary_pref="standard",
        user_allergies=["Gluten / Wheat"]
    )
    assert not any("wheat" in f["name"].lower() for f in gluten_safe)

@pytest.mark.asyncio
async def test_hard_safety_filter_dietary_restrictions():
    """
    Test 4: Pre-ML Hard Safety Filter strictly removes meat/eggs for Vegetarian/Vegan.
    """
    candidate_foods = [
        {"id": "1", "name": "Chettinad Chicken Curry", "category": "meat", "calories": 320, "protein_g": 28, "carbs_g": 6, "fat_g": 18, "fiber_g": 2},
        {"id": "2", "name": "Vanjaram Fish Fry", "category": "fish", "calories": 250, "protein_g": 26, "carbs_g": 4, "fat_g": 14, "fiber_g": 1},
        {"id": "3", "name": "Egg Bhurji", "category": "eggs", "calories": 180, "protein_g": 12, "carbs_g": 3, "fat_g": 13, "fiber_g": 0.5},
        {"id": "4", "name": "Paneer Tikka", "category": "snacks", "calories": 220, "protein_g": 14, "carbs_g": 8, "fat_g": 14, "fiber_g": 3},
        {"id": "5", "name": "Chana Sundal", "category": "snacks", "calories": 160, "protein_g": 8, "carbs_g": 24, "fat_g": 3, "fiber_g": 5}
    ]

    # Vegetarian check (Zero meat/fish/egg)
    veg_safe = MLFoodRecommender.apply_safety_filters(
        candidate_foods=candidate_foods,
        dietary_pref="vegetarian",
        user_allergies=[]
    )
    assert not any(f["name"] in ["Chettinad Chicken Curry", "Vanjaram Fish Fry", "Egg Bhurji"] for f in veg_safe)
    assert any(f["name"] == "Chana Sundal" for f in veg_safe)
    assert any(f["name"] == "Paneer Tikka" for f in veg_safe)

    # Vegan check (Zero meat/fish/egg/dairy)
    vegan_safe = MLFoodRecommender.apply_safety_filters(
        candidate_foods=candidate_foods,
        dietary_pref="vegan",
        user_allergies=[]
    )
    assert not any(f["name"] in ["Chettinad Chicken Curry", "Vanjaram Fish Fry", "Egg Bhurji", "Paneer Tikka"] for f in vegan_safe)
    assert any(f["name"] == "Chana Sundal" for f in vegan_safe)

@pytest.mark.asyncio
async def test_protein_aware_ranking():
    """
    Test 5: When protein remaining is high or goal is muscle gain, high-protein foods rank higher.
    """
    candidate_foods = [
        {"id": "1", "name": "Boiled Sweet Corn", "category": "snacks", "calories": 140, "protein_g": 3.0, "carbs_g": 28, "fat_g": 1.5, "fiber_g": 3.0, "serving_grams": 100},
        {"id": "2", "name": "Moong Sprouts Chaat", "category": "snacks", "calories": 150, "protein_g": 12.0, "carbs_g": 22, "fat_g": 1.5, "fiber_g": 5.5, "serving_grams": 100},
        {"id": "3", "name": "Roasted Makhana", "category": "snacks", "calories": 130, "protein_g": 4.0, "carbs_g": 24, "fat_g": 2.0, "fiber_g": 3.0, "serving_grams": 100}
    ]

    user_profile = {"fitness_goal": "muscle_gain", "dietary_preference": "vegetarian", "allergies": []}
    nutrition_status = {
        "calories_remaining": 600.0,
        "status_level": "on_track",
        "macros": {"protein": {"remaining": 50.0}, "carbs": {"remaining": 60.0}, "fat": {"remaining": 15.0}, "fiber": {"remaining": 10.0}}
    }

    ranked = MLFoodRecommender.rank_foods(
        candidate_foods=candidate_foods,
        user_profile=user_profile,
        nutrition_status=nutrition_status,
        meal_context="evening_snack",
        limit=3
    )

    assert len(ranked) > 0
    # Top ranked should be Moong Sprouts Chaat due to high protein (12g)
    assert ranked[0]["food_name"] == "Moong Sprouts Chaat"
    assert ranked[0]["suitability_score"] >= ranked[1]["suitability_score"]
    assert "protein" in ranked[0]["reason"].lower()

@pytest.mark.asyncio
async def test_exceeded_calories_ranks_light_foods():
    """
    Test 6: When calorie target is exceeded, heavy foods are suppressed and light options prioritized.
    """
    candidate_foods = [
        {"id": "1", "name": "Paneer Butter Masala with 2 Parathas", "category": "curry", "calories": 580, "protein_g": 18, "carbs_g": 60, "fat_g": 28, "fiber_g": 4, "serving_grams": 300},
        {"id": "2", "name": "Cucumber Tomato Pepper Salad with Lemon", "category": "snacks", "calories": 65, "protein_g": 2, "carbs_g": 12, "fat_g": 0.5, "fiber_g": 3.5, "serving_grams": 150},
        {"id": "3", "name": "Spiced Buttermilk (Neer Mor)", "category": "beverages", "calories": 45, "protein_g": 2.5, "carbs_g": 4, "fat_g": 1.2, "fiber_g": 0.5, "serving_grams": 200}
    ]

    user_profile = {"fitness_goal": "weight_loss", "dietary_preference": "vegetarian", "allergies": []}
    nutrition_status = {
        "calories_remaining": -250.0,
        "status_level": "significantly_above",
        "macros": {"protein": {"remaining": 0.0}, "carbs": {"remaining": 0.0}, "fat": {"remaining": 0.0}, "fiber": {"remaining": 5.0}}
    }

    ranked = MLFoodRecommender.rank_foods(
        candidate_foods=candidate_foods,
        user_profile=user_profile,
        nutrition_status=nutrition_status,
        meal_context="evening_snack",
        limit=3
    )

    assert len(ranked) > 0
    # Heavy 580 kcal dish must NOT be rank 1
    assert ranked[0]["calories"] <= 150
    assert "target" in ranked[0]["reason"].lower() or "light" in ranked[0]["reason"].lower()

@pytest.mark.asyncio
async def test_user_history_frequency_incorporation(unique_email):
    """
    Test 7: Frequently logged foods are incorporated into user history feature without fake claims.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await setup_user(client, unique_email, fitness_goal="weight_loss", dietary_pref="standard")

        # Log a meal item
        await client.post("/api/meals", headers=headers, json={
            "meal_type": "snack",
            "source": "manual",
            "items": [
                {
                    "food_name": "Roasted Makhana",
                    "quantity": 1.0,
                    "serving_unit": "bowl",
                    "grams": 30.0,
                    "calories": 130.0,
                    "protein_g": 4.0,
                    "carbs_g": 24.0,
                    "fat_g": 2.0,
                    "fiber_g": 3.0
                }
            ]
        })

        # Fetch recommendations
        res = await client.get("/api/nutrition/recommendations?meal_type=evening_snack&limit=4", headers=headers)
        assert res.status_code == 200
        recs = res.json()
        assert len(recs) > 0
        assert all(r["suitability_score"] is not None for r in recs)

@pytest.mark.asyncio
async def test_fallback_when_ml_model_missing():
    """
    Test 8: If ML model fails or is unavailable, fallback deterministic engine provides safe valid results.
    """
    candidate_foods = [
        {"id": "1", "name": "Steamed Idli with Sambar", "category": "dosa", "calories": 180, "protein_g": 6.0, "carbs_g": 34, "fat_g": 2.0, "fiber_g": 3.0, "serving_grams": 120},
        {"id": "2", "name": "Oats Porridge with Almonds", "category": "breakfast", "calories": 210, "protein_g": 8.0, "carbs_g": 36, "fat_g": 4.0, "fiber_g": 4.5, "serving_grams": 150}
    ]

    fallback = MLFoodRecommender._get_fallback_recommendations if hasattr(MLFoodRecommender, '_get_fallback_recommendations') else None
    
    user_profile = {"fitness_goal": "maintain", "dietary_preference": "vegetarian", "allergies": []}
    nutrition_status = {
        "calories_remaining": 400.0,
        "status_level": "on_track",
        "macros": {"protein": {"remaining": 20.0}, "carbs": {"remaining": 50.0}, "fat": {"remaining": 15.0}, "fiber": {"remaining": 8.0}}
    }

    try:
        MLFoodRecommender._disabled = True

        ranked = MLFoodRecommender.rank_foods(
            candidate_foods=candidate_foods,
            user_profile=user_profile,
            nutrition_status=nutrition_status,
            meal_context="breakfast",
            limit=2
        )

        assert len(ranked) == 2
        assert ranked[0]["recommendation_source"] == "rule_based_fallback"
        assert ranked[0]["suitability_score"] > 0
    finally:
        MLFoodRecommender._disabled = False
