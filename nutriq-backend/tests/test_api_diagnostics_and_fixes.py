import pytest
import uuid
import json
import httpx
from app.main import app


@pytest.mark.asyncio
async def test_api_diagnostics_and_fixes():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User
        uid = uuid.uuid4().hex[:8]
        reg_res = await client.post("/api/auth/register", json={
            "name": "Diagnostic User",
            "email": f"diag_{uid}@example.com",
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Setup Profile & Goals
        await client.post("/api/profile", headers=headers, json={
            "name": "Diagnostic User",
            "age": 28,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 72.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "vegetarian"
        })

        await client.post("/api/goals", headers=headers, json={
            "goal_type": "weight_loss",
            "current_weight_kg": 72.0,
            "target_weight_kg": 68.0,
            "desired_rate": 0.5
        })

        # Log a meal and water
        await client.post("/api/meals", headers=headers, json={
            "meal_type": "breakfast",
            "source": "search",
            "items": [
                {
                    "food_name": "Plain Dosa",
                    "quantity": 2.0,
                    "serving_unit": "piece",
                    "grams": 160.0,
                    "calories": 269.0,
                    "protein_g": 6.2,
                    "carbs_g": 47.0,
                    "fat_g": 5.9,
                    "fiber_g": 2.9
                }
            ]
        })
        await client.post("/api/water", headers=headers, json={"amount_ml": 750})

        # =========================================================================
        # ERROR 1 FIX TEST: Meal Planner (Generate 3-Day & Retrieve Active)
        # =========================================================================
        mp_gen = await client.post("/api/ai/meal-plan", headers=headers, json={"days": 3, "budget_level": "medium"})
        assert mp_gen.status_code == 200
        plan_out = mp_gen.json()
        assert plan_out["active"] is True
        assert plan_out["title"] is not None
        plan_data = json.loads(plan_out["plan_payload"])
        assert len(plan_data["days"]) == 3
        # Ensure day 1 breakfast != day 2 breakfast
        day1 = plan_data["days"]["Monday"]
        day2 = plan_data["days"]["Tuesday"]
        assert day1["breakfast"]["name"] != day2["breakfast"]["name"]

        # Test GET /api/ai/meal-plan
        mp_get = await client.get("/api/ai/meal-plan", headers=headers)
        assert mp_get.status_code == 200
        active_plan = mp_get.json()
        assert active_plan["id"] == plan_out["id"]

        # =========================================================================
        # ERROR 2 FIX TEST: AI Assistant Grounded Queries
        # =========================================================================
        # Q1: Calories left
        chat_cal = await client.post("/api/ai/chat", headers=headers, json={
            "messages": [{"role": "user", "content": "How many calories do I have left?"}]
        })
        assert chat_cal.status_code == 200
        resp_cal = chat_cal.json()["response"]
        assert "remaining" in resp_cal.lower() or "kcal" in resp_cal.lower()

        # Q2: What did I eat today?
        chat_eat = await client.post("/api/ai/chat", headers=headers, json={
            "messages": [{"role": "user", "content": "What did I eat today?"}]
        })
        assert chat_eat.status_code == 200
        resp_eat = chat_eat.json()["response"]
        assert "Plain Dosa" in resp_eat or "Breakfast" in resp_eat

        # Q3: How much protein have I consumed?
        chat_pro = await client.post("/api/ai/chat", headers=headers, json={
            "messages": [{"role": "user", "content": "How much protein have I consumed?"}]
        })
        assert chat_pro.status_code == 200
        resp_pro = chat_pro.json()["response"]
        assert "protein" in resp_pro.lower()

        # Q4: Suggest a high-protein dinner
        chat_din = await client.post("/api/ai/chat", headers=headers, json={
            "messages": [{"role": "user", "content": "Suggest a high-protein dinner."}]
        })
        assert chat_din.status_code == 200
        resp_din = chat_din.json()["response"]
        assert ("paneer" in resp_din.lower() or "moong" in resp_din.lower() or "protein" in resp_din.lower())

        # Q5: How much water should I drink?
        chat_wat = await client.post("/api/ai/chat", headers=headers, json={
            "messages": [{"role": "user", "content": "How much water should I drink?"}]
        })
        assert chat_wat.status_code == 200
        resp_wat = chat_wat.json()["response"]
        assert "hydration" in resp_wat.lower() or "ml" in resp_wat.lower()

        # Q6: What can I eat instead of white rice?
        chat_sub = await client.post("/api/ai/chat", headers=headers, json={
            "messages": [{"role": "user", "content": "What can I eat instead of white rice?"}]
        })
        assert chat_sub.status_code == 200
        resp_sub = chat_sub.json()["response"]
        assert "millet" in resp_sub.lower() or "thinai" in resp_sub.lower() or "cauliflower" in resp_sub.lower() or "quinoa" in resp_sub.lower()

        # Ensure all 6 questions produced DIFFERENT, non-identical grounded responses
        responses = [resp_cal, resp_eat, resp_pro, resp_din, resp_wat, resp_sub]
        assert len(set(responses)) == 6, "All assistant responses must be uniquely grounded"

        # =========================================================================
        # ERROR 3 FIX TEST: Privacy & Consent + Export Downloads
        # =========================================================================
        # Test GET /api/privacy/consents
        consents_res = await client.get("/api/privacy/consents", headers=headers)
        assert consents_res.status_code == 200
        consents = consents_res.json()
        assert len(consents) >= 2  # terms_of_service and ai_processing recorded on registration

        # Test Downloads
        pdf_res = await client.get("/api/export/pdf", headers=headers)
        assert pdf_res.status_code == 200
        assert pdf_res.content.startswith(b"%PDF-")

        csv_res = await client.get("/api/export/csv", headers=headers)
        assert csv_res.status_code == 200
        assert csv_res.content.startswith(b"\xef\xbb\xbf")

        json_res = await client.get("/api/export/json", headers=headers)
        assert json_res.status_code == 200
        assert json_res.json()["profile"]["name"] == "Diagnostic User"
