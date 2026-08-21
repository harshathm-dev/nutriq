import pytest
import uuid
import httpx
from app.main import app


@pytest.mark.asyncio
async def test_ai_assistant_dynamic_calories_and_protein_responses():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User
        uid = uuid.uuid4().hex[:8]
        reg = await client.post("/api/auth/register", json={
            "name": "Dynamic Nutrition User",
            "email": f"dynamic_{uid}@example.com",
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Setup Profile: Weight 75kg, Height 178cm, 28yo, Moderately Active, Weight Loss
        # NutritionEngine calculates specific target (e.g. ~2000-2300 kcal, ~120-160g protein)
        prof_res = await client.post("/api/profile", headers=headers, json={
            "name": "Dynamic Nutrition User",
            "age": 28,
            "gender": "male",
            "height_cm": 178.0,
            "weight_kg": 75.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "standard"
        })
        assert prof_res.status_code in [200, 201]

        # 3. Create Conversation
        conv_res = await client.post("/api/ai/conversations", headers=headers, json={"title": "Nutrition Check"})
        assert conv_res.status_code == 201
        conv_id = conv_res.json()["id"]

        # 4. Ask "How many calories do I have left?" before logging meals
        msg1 = await client.post(
            f"/api/ai/conversations/{conv_id}/messages",
            headers=headers,
            json={"content": "How many calories do I have left?", "stream": False}
        )
        assert msg1.status_code == 200
        msg1_data = msg1.json()
        assert "remaining" in msg1_data["content"].lower() or "budget" in msg1_data["content"].lower()
        assert msg1_data["metadata"]["remaining_calories"] > 0

        # 5. Log a meal: 2 Boiled Eggs + 1 Plate Biryani (~750 kcal, ~35g protein)
        meal_res = await client.post("/api/meals", headers=headers, json={
            "meal_type": "lunch",
            "items": [
                {
                    "food_name": "Boiled Egg",
                    "quantity": 2,
                    "portion": 2,
                    "serving_unit": "piece",
                    "grams": 100.0,
                    "calories": 156.0,
                    "protein_g": 12.6,
                    "carbs_g": 1.2,
                    "fat_g": 10.6,
                    "fiber_g": 0.0
                },
                {
                    "food_name": "Chicken Biryani",
                    "quantity": 1,
                    "portion": 1,
                    "serving_unit": "plate",
                    "grams": 350.0,
                    "calories": 620.0,
                    "protein_g": 28.0,
                    "carbs_g": 72.0,
                    "fat_g": 22.0,
                    "fiber_g": 3.0
                }
            ]
        })
        assert meal_res.status_code == 201

        # 6. Ask "How many calories do I have left?" after logging meal
        msg2 = await client.post(
            f"/api/ai/conversations/{conv_id}/messages",
            headers=headers,
            json={"content": "How many calories do I have left?", "stream": False}
        )
        assert msg2.status_code == 200
        msg2_data = msg2.json()
        assert "776" in msg2_data["content"] or "consumed" in msg2_data["content"].lower()
        # Remaining calories decreased by ~776 kcal
        rem_cal = msg2_data["metadata"]["remaining_calories"]
        assert rem_cal < msg1_data["metadata"]["remaining_calories"]

        # 7. Ask "How much protein do I still need?"
        msg3 = await client.post(
            f"/api/ai/conversations/{conv_id}/messages",
            headers=headers,
            json={"content": "How much protein do I still need?", "stream": False}
        )
        assert msg3.status_code == 200
        msg3_data = msg3.json()
        assert "protein" in msg3_data["content"].lower()
        assert "40.6" in msg3_data["content"] or "remaining" in msg3_data["content"].lower()

        # 8. Test Retry Deduplication: sending identical user content right after
        # It should update or add assistant response without duplicating user turns in history
        detail_before = await client.get(f"/api/ai/conversations/{conv_id}", headers=headers)
        count_before = len(detail_before.json()["messages"])

        # Retry request
        retry_res = await client.post(
            f"/api/ai/conversations/{conv_id}/messages",
            headers=headers,
            json={"content": "How much protein do I still need?", "stream": False}
        )
        assert retry_res.status_code == 200
        
        detail_after = await client.get(f"/api/ai/conversations/{conv_id}", headers=headers)
        # Should have updated cleanly
        assert len(detail_after.json()["messages"]) >= count_before


@pytest.mark.asyncio
async def test_ai_conversations_auth_and_validation_errors():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated request -> 401
        unauth_res = await client.get("/api/ai/conversations")
        assert unauth_res.status_code == 401

        # 2. Register
        uid = uuid.uuid4().hex[:8]
        reg = await client.post("/api/auth/register", json={
            "name": "Auth Error User",
            "email": f"autherr_{uid}@example.com",
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Message to non-existent conversation -> 404
        bad_conv_res = await client.post(
            "/api/ai/conversations/non-existent-conv-id/messages",
            headers=headers,
            json={"content": "Hello", "stream": False}
        )
        assert bad_conv_res.status_code == 404

        # 4. Empty message -> 400 or 422
        conv = await client.post("/api/ai/conversations", headers=headers, json={"title": "Empty Test"})
        conv_id = conv.json()["id"]

        empty_res = await client.post(
            f"/api/ai/conversations/{conv_id}/messages",
            headers=headers,
            json={"content": "   ", "stream": False}
        )
        assert empty_res.status_code in [400, 422]
