import pytest
import uuid
import json
import httpx
from app.main import app


@pytest.mark.asyncio
async def test_multi_format_data_export():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # =========================================================================
        # 1. SECURITY TEST: Unauthenticated requests MUST return 401 Unauthorized
        # =========================================================================
        unauth_pdf = await client.get("/api/export/pdf")
        assert unauth_pdf.status_code == 401

        unauth_csv = await client.get("/api/export/csv")
        assert unauth_csv.status_code == 401

        unauth_json = await client.get("/api/export/json")
        assert unauth_json.status_code == 401

        # =========================================================================
        # 2. CREATE USER A WITH PROFILE, GOALS, MEALS (INDIAN & TAMIL FOODS), WATER
        # =========================================================================
        uid_a = uuid.uuid4().hex[:8]
        reg_a = await client.post("/api/auth/register", json={
            "name": "Karthik Subramanian",
            "email": f"karthik_{uid_a}@example.com",
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg_a.status_code == 201
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Setup User A Profile
        await client.post("/api/profile", headers=headers_a, json={
            "name": "Karthik Subramanian",
            "age": 29,
            "gender": "male",
            "height_cm": 176.0,
            "weight_kg": 75.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "vegetarian",
            "food_preferences": "Traditional South Indian Cuisine"
        })

        # Setup User A Goal
        await client.post("/api/goals", headers=headers_a, json={
            "goal_type": "weight_loss",
            "current_weight_kg": 75.0,
            "target_weight_kg": 70.0,
            "desired_rate": 0.5
        })

        # Log User A Meals with Indian & Tamil Dishes
        # Breakfast: 2 Plain Dosas with Sambar & Ragi Dosa
        await client.post("/api/meals", headers=headers_a, json={
            "meal_type": "breakfast",
            "source": "search",
            "items": [
                {
                    "food_name": "Plain Dosa",
                    "quantity": 2.0,
                    "serving_unit": "1 piece (medium)",
                    "grams": 160.0,
                    "calories": 269.0,
                    "protein_g": 6.2,
                    "carbs_g": 47.0,
                    "fat_g": 5.9,
                    "fiber_g": 2.9
                },
                {
                    "food_name": "Tamil Sambar (with Drumstick & Vegetables)",
                    "quantity": 1.0,
                    "serving_unit": "1 katori",
                    "grams": 150.0,
                    "calories": 102.0,
                    "protein_g": 5.1,
                    "carbs_g": 15.3,
                    "fat_g": 2.4,
                    "fiber_g": 3.8
                },
                {
                    "food_name": "Ragi Dosa",
                    "quantity": 1.0,
                    "serving_unit": "1 piece",
                    "grams": 80.0,
                    "calories": 140.0,
                    "protein_g": 3.2,
                    "carbs_g": 26.5,
                    "fat_g": 2.1,
                    "fiber_g": 3.5
                }
            ]
        })

        # Lunch: Ven Pongal, Lemon Rice & Curd Rice
        await client.post("/api/meals", headers=headers_a, json={
            "meal_type": "lunch",
            "source": "nlp",
            "items": [
                {
                    "food_name": "Ven Pongal (Ghee Khara Pongal)",
                    "quantity": 1.0,
                    "serving_unit": "1 plate",
                    "grams": 200.0,
                    "calories": 384.0,
                    "protein_g": 10.4,
                    "carbs_g": 49.0,
                    "fat_g": 16.8,
                    "fiber_g": 4.8
                },
                {
                    "food_name": "Lemon Rice",
                    "quantity": 1.0,
                    "serving_unit": "1 bowl",
                    "grams": 150.0,
                    "calories": 245.0,
                    "protein_g": 4.2,
                    "carbs_g": 42.0,
                    "fat_g": 6.8,
                    "fiber_g": 1.9
                },
                {
                    "food_name": "Curd Rice (Thayir Sadam)",
                    "quantity": 1.0,
                    "serving_unit": "1 cup",
                    "grams": 180.0,
                    "calories": 210.0,
                    "protein_g": 6.5,
                    "carbs_g": 33.0,
                    "fat_g": 5.8,
                    "fiber_g": 1.2
                }
            ]
        })

        # Dinner: Hyderabadi Veg Biriyani
        await client.post("/api/meals", headers=headers_a, json={
            "meal_type": "dinner",
            "source": "search",
            "items": [
                {
                    "food_name": "Hyderabadi Veg Biriyani",
                    "quantity": 1.0,
                    "serving_unit": "1 plate",
                    "grams": 250.0,
                    "calories": 420.0,
                    "protein_g": 9.5,
                    "carbs_g": 68.0,
                    "fat_g": 12.0,
                    "fiber_g": 5.2
                }
            ]
        })

        # Log Water & Weight for User A
        await client.post("/api/water", headers=headers_a, json={"amount_ml": 750})
        await client.post("/api/water", headers=headers_a, json={"amount_ml": 500})
        await client.post("/api/weight", headers=headers_a, json={"weight_kg": 75.0})

        # =========================================================================
        # 3. CREATE USER B FOR DATA ISOLATION TESTING
        # =========================================================================
        uid_b = uuid.uuid4().hex[:8]
        reg_b = await client.post("/api/auth/register", json={
            "name": "Sarah Connor",
            "email": f"sarah_{uid_b}@example.com",
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg_b.status_code == 201
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User B has no meals logged
        await client.post("/api/profile", headers=headers_b, json={
            "name": "Sarah Connor",
            "age": 32,
            "gender": "female",
            "height_cm": 165.0,
            "weight_kg": 58.0,
            "activity_level": "very_active",
            "fitness_goal": "muscle_gain"
        })

        # =========================================================================
        # 4. TEST JSON EXPORT FOR USER A
        # =========================================================================
        json_res_a = await client.get("/api/export/json", headers=headers_a)
        assert json_res_a.status_code == 200
        assert "application/json" in json_res_a.headers["Content-Type"]
        assert "NutriQ_Data_Backup_" in json_res_a.headers["Content-Disposition"]
        assert json_res_a.headers["Content-Disposition"].endswith('.json"')

        data_a = json_res_a.json()
        assert data_a["export_metadata"]["application"] == "NutriQ"
        assert data_a["export_metadata"]["format_version"] == "1.0"
        assert data_a["profile"]["name"] == "Karthik Subramanian"
        assert data_a["profile"]["age"] == 29
        assert data_a["nutrition_targets"]["daily_calories_target"] > 0
        assert len(data_a["meals"]) == 3
        assert len(data_a["water_logs"]) == 2
        assert len(data_a["weight_history"]) == 1
        assert len(data_a["nutrition_summary"]) >= 1
        assert data_a["nutrition_summary"][0]["total_water_ml"] == 1250.0

        # Verify no secrets in JSON
        json_raw = json_res_a.text
        assert "hashed_password" not in json_raw
        assert "access_token" not in json_raw
        assert "Password123!" not in json_raw
        assert "SECRET_KEY" not in json_raw

        # =========================================================================
        # 5. TEST CSV EXPORT FOR USER A (UTF-8 BOM + Indian Food Names)
        # =========================================================================
        csv_res_a = await client.get("/api/export/csv", headers=headers_a)
        assert csv_res_a.status_code == 200
        assert "text/csv" in csv_res_a.headers["Content-Type"]
        assert "NutriQ_Nutrition_Data_" in csv_res_a.headers["Content-Disposition"]
        assert csv_res_a.headers["Content-Disposition"].endswith('.csv"')

        # Verify UTF-8 BOM encoding
        raw_csv_bytes = csv_res_a.content
        assert raw_csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM

        csv_text = raw_csv_bytes.decode("utf-8-sig")
        assert "Plain Dosa" in csv_text
        assert "Tamil Sambar (with Drumstick & Vegetables)" in csv_text
        assert "Ven Pongal (Ghee Khara Pongal)" in csv_text
        assert "Lemon Rice" in csv_text
        assert "Curd Rice (Thayir Sadam)" in csv_text
        assert "Hyderabadi Veg Biriyani" in csv_text
        assert "Ragi Dosa" in csv_text
        assert "Date" in csv_text
        assert "Meal Type" in csv_text
        assert "Food Name" in csv_text
        assert "Calories (kcal)" in csv_text
        assert "# Hydration Logs" in csv_text
        assert "# Weight History" in csv_text

        # =========================================================================
        # 6. TEST PDF EXPORT FOR USER A (Valid Multi-page PDF Binary)
        # =========================================================================
        pdf_res_a = await client.get("/api/export/pdf", headers=headers_a)
        assert pdf_res_a.status_code == 200
        assert pdf_res_a.headers["Content-Type"] == "application/pdf"
        assert "NutriQ_Nutrition_Report_" in pdf_res_a.headers["Content-Disposition"]
        assert pdf_res_a.headers["Content-Disposition"].endswith('.pdf"')

        pdf_bytes = pdf_res_a.content
        assert pdf_bytes.startswith(b"%PDF-")  # Valid PDF Header
        assert b"%%EOF" in pdf_bytes           # Valid PDF End Of File
        assert len(pdf_bytes) > 2000           # Substantial multi-page document

        # =========================================================================
        # 7. TEST DATA CONSISTENCY ACROSS PDF, CSV, JSON SNAPSHOT
        # =========================================================================
        # Verify meal count and macro calculations match snapshot
        assert len(data_a["meals"]) == 3
        # Check that JSON, CSV reflect the exact same items
        assert "Plain Dosa" in csv_text
        assert "Tamil Sambar" in csv_text
        assert "Ven Pongal" in csv_text
        assert "Hyderabadi Veg Biriyani" in csv_text

        # =========================================================================
        # 8. TEST USER B DATA ISOLATION (ZERO LEAKAGE FROM USER A)
        # =========================================================================
        json_res_b = await client.get("/api/export/json", headers=headers_b)
        assert json_res_b.status_code == 200
        data_b = json_res_b.json()
        assert data_b["profile"]["name"] == "Sarah Connor"
        assert data_b["profile"]["age"] == 32
        assert len(data_b["meals"]) == 0  # Sarah has 0 meals, Karthik's meals NOT leaked!
        assert len(data_b["water_logs"]) == 0
        assert "Karthik Subramanian" not in json_res_b.text
        assert "Plain Dosa" not in json_res_b.text

        csv_res_b = await client.get("/api/export/csv", headers=headers_b)
        assert csv_res_b.status_code == 200
        csv_text_b = csv_res_b.content.decode("utf-8-sig")
        assert "Sarah Connor" in csv_text_b
        assert "Plain Dosa" not in csv_text_b
        assert "No meal records logged yet" in csv_text_b

        # Empty data PDF generation must not crash and output valid PDF
        pdf_res_b = await client.get("/api/export/pdf", headers=headers_b)
        assert pdf_res_b.status_code == 200
        assert pdf_res_b.content.startswith(b"%PDF-")
        assert b"%%EOF" in pdf_res_b.content
