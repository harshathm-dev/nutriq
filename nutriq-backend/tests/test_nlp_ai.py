import pytest
from app.services.ai_service import AIService
from app.services.agent_service import AgentOrchestrator, NutritionAgent, GoalAgent

@pytest.mark.asyncio
async def test_extract_food_from_natural_language_direct():
    # Test natural language extraction heuristics
    res = await AIService.extract_food_from_natural_language(
        session=None,
        user_id="test-user",
        text="two boiled eggs and two chapatis for breakfast",
        meal_type="breakfast"
    )
    assert len(res.items) >= 2
    names = [i.food_name for i in res.items]
    assert any("Boiled Egg" in n for n in names)
    assert any("Chapati" in n for n in names)
    assert res.total_calories > 300
    assert res.total_protein_g > 15

def test_agentic_pipeline_execution():
    context = {
        "user_context": {
            "consumed_calories": 1850.0,
            "target_calories": 2000.0,
            "consumed_protein_g": 95.0,
            "target_protein_g": 110.0
        },
        "goal_data": {
            "current_weight_kg": 72.0,
            "target_weight_kg": 68.0,
            "goal_type": "weight_loss"
        },
        "weight_history": [74.0, 73.0, 72.0],
        "remaining_calories": 150.0,
        "remaining_protein_g": 15.0,
        "dietary_pref": "standard",
        "logging_days": 6
    }
    result = AgentOrchestrator.execute_pipeline(context)
    assert "nutrition_telemetry" in result
    assert "goal_telemetry" in result
    assert "recommendations" in result
    assert "progress_score" in result
    assert result["progress_score"]["consistency_score"] >= 80
