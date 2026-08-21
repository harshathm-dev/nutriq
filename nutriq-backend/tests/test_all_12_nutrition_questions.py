import pytest
import uuid
import httpx
from app.main import app


@pytest.mark.asyncio
async def test_all_12_nutrition_questions_receive_grounded_real_responses():
    """
    Validates that all 12 required predefined & freeform nutrition questions
    produce real, mathematically grounded responses with no generic fallback messages.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User
        uid = uuid.uuid4().hex[:8]
        reg = await client.post("/api/auth/register", json={
            "name": "Nutrition Q&A Tester",
            "email": f"tester_{uid}@example.com",
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Setup Profile: Weight 72kg, Height 175cm, 26yo, Moderately Active, Weight Loss
        prof_res = await client.post("/api/profile", headers=headers, json={
            "name": "Nutrition Q&A Tester",
            "age": 26,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 72.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "standard"
        })
        assert prof_res.status_code in [200, 201]

        # 3. Create Conversation
        conv_res = await client.post("/api/ai/conversations", headers=headers, json={"title": "Comprehensive AI Test"})
        assert conv_res.status_code == 201
        conv_id = conv_res.json()["id"]

        # The 12 mandatory questions from requirements
        questions = [
            ("How many calories do I have left?", ["remaining", "target", "calorie"]),
            ("Am I within my calorie goal?", ["budget", "target", "track", "within"]),
            ("How many calories should dinner have?", ["dinner", "kcal", "protein"]),
            ("Suggest breakfast.", ["breakfast", "idli", "egg", "toast", "poha", "protein"]),
            ("Suggest lunch.", ["lunch", "phulka", "dal", "paneer", "chicken", "salad"]),
            ("Suggest dinner.", ["dinner", "protein", "bhurji", "tikka", "phulka", "rasam"]),
            ("Give me a meal under 400 calories.", ["400", "kcal", "protein", "phulka", "paneer"]),
            ("How much protein do I need?", ["target", "protein", "remaining", "paneer", "egg"]),
            ("How much water should I drink?", ["water", "ml", "hydration", "target"]),
            ("Am I progressing toward my goal?", ["goal", "target", "progress", "weight loss"]),
            ("What should I eat for weight loss?", ["weight loss", "protein", "fiber", "deficit"]),
            ("Suggest Indian food.", ["indian", "sambar", "idli", "phulka", "dal", "paneer"])
        ]

        for q_text, expected_keywords in questions:
            res = await client.post(
                f"/api/ai/conversations/{conv_id}/messages",
                headers=headers,
                json={"content": q_text, "stream": False}
            )
            assert res.status_code == 200, f"Failed on question: {q_text}"
            data = res.json()
            content = data["content"].lower()

            # Must NEVER return the generic off-topic boundary for valid nutrition questions
            assert "outside my nutrition focus" not in content, f"Question '{q_text}' returned off-topic message: {content}"
            assert "unable to generate a response" not in content, f"Question '{q_text}' returned error fallback: {content}"

            # Must contain relevant grounded nutrition keywords
            has_keyword = any(kw in content for kw in expected_keywords)
            assert has_keyword, f"Question '{q_text}' did not contain expected keywords {expected_keywords}. Got: {content}"

            # Metadata must be valid and non-zero
            metadata = data.get("metadata", {})
            assert "remaining_calories" in metadata
            assert "remaining_protein" in metadata
            assert metadata["remaining_calories"] > 0
            assert metadata["remaining_protein"] > 0
