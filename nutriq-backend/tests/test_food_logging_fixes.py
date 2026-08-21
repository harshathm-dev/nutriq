import pytest
import uuid
import httpx
from app.main import app

@pytest.mark.asyncio
async def test_food_logging_simplified_and_fixed():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create unique user for meal logging tests
        uid = uuid.uuid4().hex[:8]
        reg_res = await client.post("/api/auth/register", json={
            "name": "Food Log Tester",
            "email": f"food_tester_{uid}@example.com",
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Setup complete profile
        await client.post("/api/profile", headers=headers, json={
            "name": "Food Log Tester",
            "age": 28,
            "gender": "male",
            "height_cm": 178.0,
            "weight_kg": 74.0,
            "activity_level": "moderately_active",
            "fitness_goal": "maintain"
        })

        # =========================================================================
        # 1. TEST FOOD SEARCH: Plain Dosa & Regional Dishes
        # =========================================================================
        search_res = await client.get("/api/foods?query=Plain Dosa")
        assert search_res.status_code == 200
        foods = search_res.json()
        assert len(foods) > 0
        plain_dosa = next((f for f in foods if "Plain Dosa" in f["name"]), None)
        assert plain_dosa is not None
        assert plain_dosa["calories"] == 168.0  # per 100g base
        assert len(plain_dosa["serving_conversions"]) >= 2

        # Verify serving conversions
        piece_conv = next(c for c in plain_dosa["serving_conversions"] if "piece" in c["serving_label"])
        large_conv = next(c for c in plain_dosa["serving_conversions"] if "large" in c["serving_label"])
        assert piece_conv["grams"] == 80.0
        assert large_conv["grams"] == 120.0

        # =========================================================================
        # 2. TEST DETERMINISTIC QUANTITY & SERVING MATH
        # =========================================================================
        # 1 piece (80g): 80 * 168 / 100 = 134.4 kcal
        cal_1_piece = round((80.0 * 1.0 / 100.0) * plain_dosa["calories"])
        assert cal_1_piece == 134

        # 2 pieces (160g): 160 * 168 / 100 = 268.8 kcal -> 269 kcal
        cal_2_piece = round((80.0 * 2.0 / 100.0) * plain_dosa["calories"])
        assert cal_2_piece == 269
        assert cal_2_piece != cal_1_piece

        # 1 large dosa (120g): 120 * 168 / 100 = 201.6 kcal -> 202 kcal
        cal_1_large = round((120.0 * 1.0 / 100.0) * plain_dosa["calories"])
        assert cal_1_large == 202
        assert cal_1_large != cal_1_piece

        # =========================================================================
        # 3. TEST MEAL CREATION & JOURNAL PERSISTENCE
        # =========================================================================
        meal_res = await client.post("/api/meals", headers=headers, json={
            "meal_type": "breakfast",
            "source": "search",
            "items": [
                {
                    "food_id": plain_dosa["id"],
                    "food_name": "Plain Dosa",
                    "quantity": 2.0,
                    "serving_unit": "1 piece (medium)",
                    "unit_grams": 80.0,
                    "grams": 160.0,
                    "calories": 269.0,
                    "protein_g": 6.2,
                    "carbs_g": 47.0,
                    "fat_g": 5.9
                }
            ]
        })
        assert meal_res.status_code == 201
        created_meal = meal_res.json()
        assert created_meal["meal_type"] == "breakfast"
        assert len(created_meal["items"]) == 1
        assert created_meal["items"][0]["food_name"] == "Plain Dosa"
        assert created_meal["items"][0]["quantity"] == 2.0
        assert round(created_meal["items"][0]["calories"]) == 269

        # Verify meal appears in journal
        get_meals_res = await client.get("/api/meals", headers=headers)
        assert get_meals_res.status_code == 200
        all_meals = get_meals_res.json()
        assert len(all_meals) >= 1
        logged = next(m for m in all_meals if m["id"] == created_meal["id"])
        assert round(logged["totals"]["calories"]) == 269

        # =========================================================================
        # 4. TEST AI NATURAL TEXT EXTRACTION (Valid input with quantities)
        # =========================================================================
        nlp_res = await client.post("/api/ai/analyze-food", headers=headers, json={
            "text": "I ate 2 boiled eggs and one banana for breakfast",
            "meal_type": "lunch"  # Should infer "breakfast" from text
        })
        assert nlp_res.status_code == 200
        nlp_data = nlp_res.json()
        assert nlp_data["inferred_meal_type"] == "breakfast"
        assert len(nlp_data["items"]) == 2

        egg_item = next(i for i in nlp_data["items"] if "Egg" in i["food_name"])
        banana_item = next(i for i in nlp_data["items"] if "Banana" in i["food_name"])

        assert egg_item["quantity"] == 2.0
        assert egg_item["calories"] == 156.0  # 2 * 78 kcal
        assert egg_item["protein_g"] == 12.6  # 2 * 6.3g

        assert banana_item["quantity"] == 1.0
        assert banana_item["calories"] == 105.0
        assert banana_item["carbs_g"] == 26.9

        assert nlp_data["total_calories"] == 261.0

        # =========================================================================
        # 5. TEST AI NATURAL TEXT UNKNOWN INPUT (No fake nutrition hallucination)
        # =========================================================================
        nlp_unknown_res = await client.post("/api/ai/analyze-food", headers=headers, json={
            "text": "xyzzy foo bar 98765 random query",
            "meal_type": "breakfast"
        })
        assert nlp_unknown_res.status_code == 400
        assert "I couldn't identify that food" in nlp_unknown_res.json()["detail"]

        # =========================================================================
        # 6. TEST PACKAGED FOOD BARCODE LOOKUP (Valid Barcode)
        # =========================================================================
        # Amul Taaza Milk: 8901262010115
        bc_valid_res = await client.get("/api/foods/barcode/8901262010115")
        assert bc_valid_res.status_code == 200
        bc_food = bc_valid_res.json()
        assert "Amul Taaza" in bc_food["name"]
        assert bc_food["barcode"] == "8901262010115"
        assert bc_food["calories"] == 58.0  # per 100ml
        assert len(bc_food["serving_conversions"]) >= 1

        # =========================================================================
        # 7. TEST PACKAGED FOOD BARCODE LOOKUP (Unknown Barcode -> Strict 404)
        # =========================================================================
        bc_invalid_res = await client.get("/api/foods/barcode/9999999999999")
        assert bc_invalid_res.status_code == 404
        assert "couldn't find this packaged food" in bc_invalid_res.json()["detail"].lower()
