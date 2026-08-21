import pytest
import uuid
import json
import base64
from datetime import datetime, timezone
import httpx
from app.utils.date_utils import get_today_local

@pytest.mark.asyncio
async def test_live_25_step_end_to_end_journey():
    """
    PHASE 35: 25-Step End-to-End User Journey against live backend (http://127.0.0.1:8000)
    """
    base_url = "http://127.0.0.1:8000"
    uid = uuid.uuid4().hex[:8]
    user_email = f"e2e_journey_{uid}@nutriq.app"
    user_pass = "SecureE2EPass123!"
    user_name = f"E2E Voyager {uid}"

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Step 1 & 2: Health & Discovery
        health_res = await client.get("/health")
        assert health_res.status_code == 200

        # Step 3 & 4: Create account & Welcome Email Trigger
        reg_res = await client.post("/api/auth/register", json={
            "name": user_name,
            "email": user_email,
            "password": user_pass,
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Step 5: Complete profile
        prof_res = await client.post("/api/profile", headers=auth_headers, json={
            "name": user_name,
            "age": 29,
            "gender": "male",
            "height_cm": 178.0,
            "weight_kg": 76.0,
            "activity_level": "moderately_active",
            "fitness_goal": "maintain",
            "dietary_preference": "standard"
        })
        assert prof_res.status_code in [200, 201]

        # Step 6: Open dashboard targets
        me_res = await client.get("/api/auth/me", headers=auth_headers)
        assert me_res.status_code == 200

        # Step 7: Search Indian food database
        search_dosa = await client.get("/api/foods?query=Dosa")
        assert search_dosa.status_code == 200
        dosa_item = search_dosa.json()[0]

        search_biryani = await client.get("/api/foods?query=Biryani")
        assert search_biryani.status_code == 200
        biryani_item = search_biryani.json()[0]

        # Step 8: Log Breakfast
        b_res = await client.post("/api/meals", headers=auth_headers, json={
            "meal_type": "breakfast",
            "source": "manual",
            "items": [{
                "food_id": dosa_item["id"],
                "food_name": dosa_item["name"],
                "quantity": 2.0,
                "serving_unit": "piece",
                "grams": 200.0,
                "calories": float(dosa_item["calories"]) * 2.0,
                "protein_g": float(dosa_item.get("protein_g", 0.0) or 0.0) * 2.0,
                "carbs_g": float(dosa_item.get("carbs_g", 0.0) or 0.0) * 2.0,
                "fat_g": float(dosa_item.get("fat_g", 0.0) or 0.0) * 2.0,
                "fiber_g": float(dosa_item.get("fiber_g", 0.0) or 0.0) * 2.0
            }]
        })
        assert b_res.status_code in [200, 201]

        # Step 9: Log Lunch
        l_res = await client.post("/api/meals", headers=auth_headers, json={
            "meal_type": "lunch",
            "source": "manual",
            "items": [{
                "food_id": biryani_item["id"],
                "food_name": biryani_item["name"],
                "quantity": 1.0,
                "serving_unit": "plate",
                "grams": 250.0,
                "calories": float(biryani_item["calories"]),
                "protein_g": float(biryani_item.get("protein_g", 0.0) or 0.0),
                "carbs_g": float(biryani_item.get("carbs_g", 0.0) or 0.0),
                "fat_g": float(biryani_item.get("fat_g", 0.0) or 0.0),
                "fiber_g": float(biryani_item.get("fiber_g", 0.0) or 0.0)
            }]
        })
        assert l_res.status_code in [200, 201]

        # Step 10: Log Snack
        s_res = await client.post("/api/meals", headers=auth_headers, json={
            "meal_type": "snack",
            "source": "manual",
            "items": [{
                "food_id": dosa_item["id"],
                "food_name": "Roasted Makhana",
                "quantity": 1.0,
                "serving_unit": "bowl",
                "grams": 30.0,
                "calories": 130.0,
                "protein_g": 4.0,
                "carbs_g": 24.0,
                "fat_g": 2.0,
                "fiber_g": 3.0
            }]
        })
        assert s_res.status_code in [200, 201]

        # Step 11: Log Dinner
        d_res = await client.post("/api/meals", headers=auth_headers, json={
            "meal_type": "dinner",
            "source": "manual",
            "items": [{
                "food_id": dosa_item["id"],
                "food_name": "Whole Wheat Phulkas & Paneer",
                "quantity": 1.0,
                "serving_unit": "plate",
                "grams": 200.0,
                "calories": 380.0,
                "protein_g": 18.0,
                "carbs_g": 44.0,
                "fat_g": 14.0,
                "fiber_g": 6.0
            }]
        })
        assert d_res.status_code in [200, 201]

        # Step 12 & 13: Check Daily Summary
        today_iso = get_today_local().isoformat()
        ds_res = await client.get(f"/api/daily-summary?date={today_iso}", headers=auth_headers)
        assert ds_res.status_code == 200
        ds = ds_res.json()
        assert ds["calories"]["consumed"] > 0
        assert ds["meals"]["breakfast"]["logged"] is True
        assert ds["meals"]["lunch"]["logged"] is True

        # Step 14: Generate Meal Plan
        plan_a_res = await client.post("/api/ai/meal-plan", headers=auth_headers, json={"days": 3, "budget_level": "medium"})
        assert plan_a_res.status_code == 200
        plan_a = plan_a_res.json()
        plan_a_id = plan_a["id"]
        plan_a_payload = json.loads(plan_a["plan_payload"])

        # Step 15: Regenerate Meal Plan (guaranteed distinct)
        plan_b_res = await client.post("/api/ai/meal-plan", headers=auth_headers, json={
            "days": 3,
            "budget_level": "medium",
            "mode": "regenerate",
            "previous_plan_id": plan_a_id,
            "regeneration_id": f"e2e_regen_{uuid.uuid4().hex[:8]}"
        })
        assert plan_b_res.status_code == 200
        plan_b = plan_b_res.json()
        plan_b_payload = json.loads(plan_b["plan_payload"])
        assert plan_b_payload["days"] != plan_a_payload["days"]

        # Step 16: AI Assistant Chat
        chat_res = await client.post("/api/ai/chat", headers=auth_headers, json={
            "messages": [{"role": "user", "content": "What is a healthy post-workout meal?"}]
        })
        assert chat_res.status_code == 200
        assert len(chat_res.json()["response"]) > 10

        # Step 17: Reminders Settings
        rem_res = await client.get("/api/reminders/settings", headers=auth_headers)
        assert rem_res.status_code == 200

        # Step 18: Analytics
        ana_daily = await client.get("/api/analytics/daily", headers=auth_headers)
        assert ana_daily.status_code == 200
        ana_weekly = await client.get("/api/analytics/weekly", headers=auth_headers)
        assert ana_weekly.status_code == 200

        # Step 19: PDF Export
        pdf_res = await client.get("/api/export/pdf", headers=auth_headers)
        assert pdf_res.status_code == 200
        assert pdf_res.headers.get("content-type") == "application/pdf"
        assert pdf_res.content.startswith(b"%PDF")

        # Step 20: CSV Export
        csv_res = await client.get("/api/export/csv", headers=auth_headers)
        assert csv_res.status_code == 200
        assert "Date,Time,Meal Type,Food Name,Quantity,Serving Unit" in csv_res.text

        # Step 21: JSON Export
        json_res = await client.get("/api/export/json", headers=auth_headers)
        assert json_res.status_code == 200
        assert "meals" in json_res.json()

        # Step 22: Logout (client-side token removal)

        # Step 23 & 24: Login again & Login Alert Trigger
        re_login = await client.post("/api/auth/login", json={
            "email": user_email,
            "password": user_pass
        })
        assert re_login.status_code == 200
        new_token = re_login.json()["access_token"]
        new_headers = {"Authorization": f"Bearer {new_token}"}

        # Step 25: Verify data persists
        meals_res = await client.get("/api/meals", headers=new_headers)
        assert meals_res.status_code == 200
        assert len(meals_res.json()) >= 4
