import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.models.profile import UserProfile
from app.models.goal import Goal
from app.models.family import Allergy
from app.models.food import Food
from app.services.food_service import FoodService
from app.services.gemini_service import GeminiService
from app.services.ai_service import AIService

@pytest.mark.asyncio
async def test_curries_and_gravies_category_returns_foods():
    async with AsyncSessionLocal() as session:
        # Test various case variations and formats of Curries & Gravies
        for cat_name in ["Curries & Gravies", "curries & gravies", "curry", "Curry", "gravies", "curries_gravies"]:
            results = await FoodService.search_foods(session, category=cat_name, limit=50)
            assert len(results) > 0, f"Failed to return foods for category: {cat_name}"
            # Verify they contain recognizable curries, dals, gravies, or kuzhambu
            names = [f.name.lower() for f in results]
            has_curry_dish = any(
                any(term in n for term in ["curry", "gravy", "dal", "kuzhambu", "korma", "kurma", "chole", "rajma", "paneer", "sambar", "kadhi", "makhani"])
                for n in names
            )
            assert has_curry_dish, f"Category results did not include curry dishes: {names[:5]}"

@pytest.mark.asyncio
async def test_search_queries_for_target_curry_terms():
    test_terms = [
        "curry",
        "gravy",
        "chicken curry",
        "paneer",
        "dal",
        "dal tadka",
        "rajma curry",
        "chana masala",
        "sambar",
        "kadhi",
        "korma"
    ]
    async with AsyncSessionLocal() as session:
        for term in test_terms:
            results = await FoodService.search_foods(session, query=term, limit=10)
            assert len(results) > 0, f"Search query '{term}' returned 0 results"
            # Verify result names relate to the query
            names = [f.name for f in results]
            assert any(term.split()[0].lower() in n.lower() or "curry" in n.lower() or "dal" in n.lower() for n in names), f"Query '{term}' returned non-matching items: {names}"

@pytest.mark.asyncio
async def test_search_ranking_prioritizes_main_dishes_over_raw_herbs():
    async with AsyncSessionLocal() as session:
        results = await FoodService.search_foods(session, query="curry", limit=10)
        assert len(results) > 0
        first_item = results[0]
        # Main curry dish should be ranked ahead of fresh curry leaves
        assert "curry leaves" not in first_item.name.lower(), f"First item was raw curry leaves instead of main dish: {first_item.name}"

@pytest.mark.asyncio
async def test_gemini_service_availability_and_fallback():
    # If GEMINI_API_KEY is not set or placeholder, is_available should be False and generate fallback
    is_avail = GeminiService.is_available()
    context = {
        "user_profile": {
            "name": "Test User",
            "dietary_preference": "vegetarian",
            "fitness_goal": "weight_loss",
            "allergies": ["peanut"]
        },
        "today": {
            "calories_consumed": 1200.0,
            "calories_remaining": 600.0,
            "protein_consumed": 45.0,
            "protein_remaining": 25.0,
            "water_consumed": 1500.0
        },
        "nutrition_target": {
            "calories": 1800.0,
            "protein": 70.0,
            "hydration": 2500.0
        },
        "recent_meals": [],
        "warnings": []
    }
    candidate_foods = [
        {
            "name": "Yellow Dal Tadka",
            "food_name": "Yellow Dal Tadka",
            "serving_label": "1 katori (150g)",
            "calories": 172.0,
            "protein_g": 10.2,
            "carbs_g": 24.8,
            "fat_g": 4.5,
            "fiber_g": 4.0,
            "reason": "Rich in protein and low in calories."
        }
    ]

    res = await GeminiService.generate_assistant_response(
        user_message="How many calories do I have left?",
        context=context,
        candidate_foods=candidate_foods
    )

    assert "answer" in res
    assert "600" in res["answer"] or "1,200" in res["answer"] or "1200" in res["answer"]
    assert res["remaining_calories"] == 600
    assert res["remaining_protein"] == 25.0
    assert "sources" in res

@pytest.mark.asyncio
async def test_grounded_ai_assistant_full_pipeline():
    async with AsyncSessionLocal() as session:
        # Create test user and profile
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email=f"test_gemini_{user_id[:8]}@nutriq.com",
            password_hash="hashed_test_password"
        )
        profile = UserProfile(
            user_id=user_id,
            name="Priya Sharma",
            age=28,
            gender="female",
            height_cm=165.0,
            weight_kg=65.0,
            activity_level="moderately_active",
            fitness_goal="weight_loss",
            dietary_preference="vegetarian"
        )
        goal = Goal(
            user_id=user_id,
            goal_type="weight_loss",
            current_weight_kg=65.0,
            target_weight_kg=60.0,
            desired_rate=0.5,
            active=True
        )
        allergy = Allergy(
            user_id=user_id,
            allergen_type="peanuts"
        )
        session.add_all([user, profile, goal, allergy])
        await session.commit()

        # 1. Remaining calories question
        resp1 = await AIService.chat_with_assistant(
            session=session,
            user_id=user_id,
            messages="How many calories do I have left today?"
        )
        assert resp1.response != ""
        assert resp1.remaining_calories is not None
        assert "NutriQ Verified Food Database" in resp1.sources

        # 2. Suggest high protein dinner
        resp2 = await AIService.chat_with_assistant(
            session=session,
            user_id=user_id,
            messages="Suggest a high-protein dinner"
        )
        assert resp2.response != ""
        assert len(resp2.suggested_actions) > 0

        # 3. What did I eat today
        resp3 = await AIService.chat_with_assistant(
            session=session,
            user_id=user_id,
            messages="What did I eat today?"
        )
        assert "logged" in resp3.response.lower() or "meals" in resp3.response.lower() or "journal" in resp3.response.lower()

        # 4. 2 dosas fit in budget
        resp4 = await AIService.chat_with_assistant(
            session=session,
            user_id=user_id,
            messages="Can I eat 2 dosas for dinner?"
        )
        assert "dosa" in resp4.response.lower()

        # 5. White rice substitute
        resp5 = await AIService.chat_with_assistant(
            session=session,
            user_id=user_id,
            messages="What can I eat instead of white rice?"
        )
        assert any(term in resp5.response.lower() for term in ["millet", "brown rice", "daliya", "quinoa", "substitute", "cauliflower"])

        # 6. Weight loss advice
        resp6 = await AIService.chat_with_assistant(
            session=session,
            user_id=user_id,
            messages="I am trying to lose weight. What should I eat tonight?"
        )
        assert resp6.response != ""

        # 7. Under 400 calories
        resp7 = await AIService.chat_with_assistant(
            session=session,
            user_id=user_id,
            messages="Give me something under 400 calories"
        )
        assert resp7.response != ""

        # 8. Water query
        resp8 = await AIService.chat_with_assistant(
            session=session,
            user_id=user_id,
            messages="How much water should I drink?"
        )
        assert any(term in resp8.response.lower() for term in ["water", "hydration", "ml"])

        # 9. Allergy safety check: Ensure peanuts are NEVER recommended to peanut-allergic user
        candidates = await AIService.get_grounded_food_candidates(
            session=session,
            user_id=user_id,
            ctx={"user_profile": {"dietary_preference": "vegetarian", "allergies": ["peanut", "peanuts"]}, "today": {"calories_remaining": 500}},
            user_message="Suggest a snack"
        )
        for c in candidates:
            c_name = (c.get("name") or c.get("food_name", "")).lower()
            assert "peanut" not in c_name and "groundnut" not in c_name, f"Allergen food leaked in candidates: {c_name}"
