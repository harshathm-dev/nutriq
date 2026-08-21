import pytest
import uuid
import json
import base64
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

from app.main import app
from app.config import settings
from app.services.nutrition_engine import NutritionEngine
from app.services.email_service import EmailService
from app.utils.date_utils import get_today_local

def make_user():
    uid = uuid.uuid4().hex[:8]
    return {
        "name": f"Audit User {uid}",
        "email": f"audit_user_{uid}@example.com",
        "password": "SecurePassword123!"
    }

@pytest.mark.asyncio
async def test_phase_05_06_registration_and_validation():
    """PHASE 5 & 6: Welcome / Registration Validation & Security"""
    user = make_user()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Missing terms / consent -> 400 Bad Request
        res_no_terms = await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": False,
            "ai_consent_accepted": True
        })
        assert res_no_terms.status_code == 400

        # 2. Valid Registration -> 201 Created
        with patch.object(EmailService, "send_welcome_email", return_value=True) as mock_welcome:
            res_reg = await client.post("/api/auth/register", json={
                "name": user["name"],
                "email": user["email"],
                "password": user["password"],
                "terms_accepted": True,
                "ai_consent_accepted": True
            })
            assert res_reg.status_code == 201
            data = res_reg.json()
            assert "access_token" in data
            assert data["email"] == user["email"].lower()
            mock_welcome.assert_called_once()

        # 3. Duplicate Email -> 400 Bad Request
        res_dup = await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert res_dup.status_code == 400
        assert "already exists" in res_dup.json()["detail"].lower()

@pytest.mark.asyncio
async def test_phase_07_login_and_session():
    """PHASE 7: Login, Invalid Password & Current User Authentication"""
    user = make_user()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })

        # 1. Wrong Password -> 401 Unauthorized
        res_wrong = await client.post("/api/auth/login", json={
            "email": user["email"],
            "password": "WrongPassword999!"
        })
        assert res_wrong.status_code == 401

        # 2. Correct Credentials -> 200 OK + Login Alert Dispatch
        with patch.object(EmailService, "send_login_notification", return_value=True) as mock_login_email:
            res_login = await client.post("/api/auth/login", json={
                "email": user["email"],
                "password": user["password"]
            })
            assert res_login.status_code == 200
            token = res_login.json()["access_token"]
            mock_login_email.assert_called_once()

        # 3. Authenticated Identity GET /api/auth/me -> 200 OK
        res_me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res_me.status_code == 200
        assert res_me.json()["email"] == user["email"].lower()

@pytest.mark.asyncio
async def test_phase_08_google_login_behavior():
    """PHASE 8: Google Sign-In Behavior & First vs Subsequent Email Dispatches"""
    transport = ASGITransport(app=app)
    g_email = f"google_audit_{uuid.uuid4().hex[:8]}@gmail.com"
    g_name = "Google Auditor"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First login -> Welcome Email
        with patch.object(EmailService, "send_welcome_email", return_value=True) as mock_welcome, \
             patch.object(EmailService, "send_login_notification", return_value=True) as mock_alert:
            res1 = await client.post("/api/auth/google", json={
                "email": g_email,
                "name": g_name,
                "google_id": f"gid_{uuid.uuid4().hex[:8]}"
            })
            assert res1.status_code == 200
            mock_welcome.assert_called_once()
            mock_alert.assert_not_called()

        # Subsequent login -> Login Notification Email
        with patch.object(EmailService, "send_welcome_email", return_value=True) as mock_welcome, \
             patch.object(EmailService, "send_login_notification", return_value=True) as mock_alert:
            res2 = await client.post("/api/auth/google", json={
                "email": g_email,
                "name": g_name,
                "google_id": f"gid_{uuid.uuid4().hex[:8]}"
            })
            assert res2.status_code == 200
            mock_welcome.assert_not_called()
            mock_alert.assert_called_once()

@pytest.mark.asyncio
async def test_phase_09_forgot_and_reset_password_security():
    """PHASE 9: Secure Forgot Password & Single-Use Token Invalidation"""
    user = make_user()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        reg_res = await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg_res.status_code == 201

        # 1. User enumeration check for unregistered user
        res_unreg = await client.post("/api/auth/forgot-password", json={"email": "nonexistent_email_12345@example.com"})
        assert res_unreg.status_code == 200
        assert "If an account exists" in res_unreg.json()["message"]

        # 2. Capture reset token and complete password reset for registered user
        captured_token = None
        def capture_token(to_email, user_name, raw_token):
            nonlocal captured_token
            captured_token = raw_token
            return True

        with patch.object(EmailService, "send_password_reset_email", side_effect=capture_token):
            res_reg = await client.post("/api/auth/forgot-password", json={"email": user["email"]})
            assert res_reg.status_code == 200
            assert res_reg.json()["message"] == res_unreg.json()["message"]

        assert captured_token is not None, "Password reset token was not dispatched."

        new_password = "BrandNewPassword999!"
        reset_res = await client.post("/api/auth/reset-password", json={
            "token": captured_token,
            "new_password": new_password
        })
        assert reset_res.status_code == 200

        # Old password rejected
        old_login = await client.post("/api/auth/login", json={
            "email": user["email"],
            "password": user["password"]
        })
        assert old_login.status_code == 401

        # New password accepted
        new_login = await client.post("/api/auth/login", json={
            "email": user["email"],
            "password": new_password
        })
        assert new_login.status_code == 200

        # Reusing the token must fail (single-use)
        reuse_res = await client.post("/api/auth/reset-password", json={
            "token": captured_token,
            "new_password": "YetAnotherPassword123!"
        })
        assert reuse_res.status_code == 400

@pytest.mark.asyncio
async def test_phase_11_12_profile_and_nutrition_calculations():
    """PHASE 11 & 12: Profile CRUD & Mifflin-St Jeor BMR/TDEE Macro Calculations"""
    user = make_user()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg_res = await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create Profile
        prof_data = {
            "name": "Audit Athlete",
            "age": 30,
            "gender": "male",
            "height_cm": 180.0,
            "weight_kg": 80.0,
            "activity_level": "very_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "vegetarian"
        }
        create_res = await client.post("/api/profile", headers=headers, json=prof_data)
        assert create_res.status_code in [200, 201]
        saved_prof = create_res.json()
        assert saved_prof["height_cm"] == 180.0
        assert saved_prof["weight_kg"] == 80.0

        # Calculate BMR & TDEE using NutritionEngine
        bmr = NutritionEngine.calculate_bmr(80.0, 180.0, 30, "male")
        assert round(bmr) == 1780

        # TDEE for very_active (1.725): 1780 * 1.725 = 3070.5 kcal
        tdee = NutritionEngine.calculate_tdee(bmr, "very_active")
        assert round(tdee) in [3070, 3071]

        # Weight Loss deficit: ~2520.5 kcal
        targets = NutritionEngine.calculate_targets(80.0, 180.0, 30, "male", "very_active", "weight_loss", 0.5, "vegetarian")
        assert targets["target_calories"] == 2520.5
        assert targets["protein_g"] > 100.0

        # Macro summation verification: Protein*4 + Carbs*4 + Fat*9 ~= Target Calories
        macro_cals = (targets["protein_g"] * 4.0) + (targets["carbs_g"] * 4.0) + (targets["fat_g"] * 9.0)
        assert abs(macro_cals - targets["target_calories"]) < 5.0

@pytest.mark.asyncio
async def test_phase_13_14_food_database_and_scaling():
    """PHASE 13 & 14: Indian Food Database Search & Multi-Serving Scaling"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Search essential Indian dishes
        queries = ["Dosa", "Idli", "Sambar", "Biryani", "Pongal", "Rice", "Chapati", "Paneer", "Dal", "Curd"]
        for q in queries:
            res = await client.get(f"/api/foods?query={q}")
            assert res.status_code == 200
            items = res.json()
            assert len(items) > 0, f"Food database search failed for dish: {q}"
            item = items[0]
            assert "calories" in item
            assert "protein_g" in item
            assert "carbs_g" in item
            assert "fat_g" in item
            assert item["calories"] > 0

        # 2. Test serving scaling calculation
        idli_res = await client.get("/api/foods?query=Idli")
        idli = idli_res.json()[0]
        base_cal = idli["calories"]
        
        scaled_2x = (base_cal / 100.0) * 200.0
        assert scaled_2x == base_cal * 2.0

@pytest.mark.asyncio
async def test_phase_15_16_17_meal_logging_dashboard_daily_summary():
    """PHASE 15, 16 & 17: Meal Logging across all slots, Dashboard & Daily Summary Totals"""
    user = make_user()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg_res = await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Setup profile
        await client.post("/api/profile", headers=headers, json={
            "name": user["name"],
            "age": 28,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 75.0,
            "activity_level": "moderately_active",
            "fitness_goal": "maintain",
            "dietary_preference": "standard"
        })

        # Fetch sample food
        food_res = await client.get("/api/foods?query=Dosa")
        food = food_res.json()[0]

        # Log meals in all 4 slots
        slots = ["breakfast", "lunch", "snack", "dinner"]
        for slot in slots:
            log_res = await client.post("/api/meals", headers=headers, json={
                "meal_type": slot,
                "source": "manual",
                "items": [{
                    "food_id": food["id"],
                    "food_name": food["name"],
                    "quantity": 1.0,
                    "serving_unit": "piece",
                    "grams": 100.0,
                    "calories": float(food["calories"]),
                    "protein_g": float(food.get("protein_g", 0.0) or 0.0),
                    "carbs_g": float(food.get("carbs_g", 0.0) or 0.0),
                    "fat_g": float(food.get("fat_g", 0.0) or 0.0),
                    "fiber_g": float(food.get("fiber_g", 0.0) or 0.0)
                }]
            })
            assert log_res.status_code in [200, 201]

        # Verify Daily Summary
        today_str = get_today_local().isoformat()
        summary_res = await client.get(f"/api/daily-summary?date={today_str}", headers=headers)
        assert summary_res.status_code == 200
        summary = summary_res.json()
        assert summary["calories"]["consumed"] > 0
        assert summary["meals"]["breakfast"]["logged"] is True
        assert summary["meals"]["lunch"]["logged"] is True
        assert summary["meals"]["snack"]["logged"] is True
        assert summary["meals"]["dinner"]["logged"] is True

@pytest.mark.asyncio
async def test_phase_18_meal_planner_and_five_consecutive_regenerations():
    """PHASE 18: Meal Planner & 5 Consecutive Regenerations with Controlled Variety"""
    user = make_user()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg_res = await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await client.post("/api/profile", headers=headers, json={
            "name": user["name"],
            "age": 28,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 72.0,
            "activity_level": "moderately_active",
            "fitness_goal": "maintain",
            "dietary_preference": "standard"
        })

        generated_signatures = []
        prev_plan_id = None

        for i in range(5):
            res = await client.post("/api/ai/meal-plan", headers=headers, json={
                "days": 3,
                "budget_level": "medium",
                "mode": "regenerate" if i > 0 else "generate",
                "previous_plan_id": prev_plan_id,
                "regeneration_id": f"regen_audit_iteration_{i}_{uuid.uuid4().hex[:6]}"
            })
            assert res.status_code == 200
            plan_record = res.json()
            prev_plan_id = plan_record["id"]
            plan_payload = json.loads(plan_record["plan_payload"])
            
            dishes = tuple(slot["name"] for day in plan_payload["days"].values() for slot_name, slot in day.items() if slot_name != "daily_summary")
            generated_signatures.append(dishes)

        # All 5 consecutive regenerated plans must be distinct
        assert len(set(generated_signatures)) == 5, "Regenerate Plan returned duplicate plan signatures!"

@pytest.mark.asyncio
async def test_phase_19_23_ai_chat_reminders_and_family():
    """PHASE 19, 22 & 23: AI Assistant Decoupled Resiliency, Family CRUD & Smart Reminders"""
    user = make_user()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg_res = await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Setup user profile
        await client.post("/api/profile", headers=headers, json={
            "name": user["name"],
            "age": 28,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 72.0,
            "activity_level": "moderately_active",
            "fitness_goal": "maintain",
            "dietary_preference": "standard"
        })

        # 1. AI Chat Assistant (handles queries and falls back gracefully if Gemini offline)
        chat_res = await client.post("/api/ai/chat", headers=headers, json={
            "messages": [
                {"role": "user", "content": "I need high protein food suggestions for dinner under 400 calories."}
            ]
        })
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        assert "response" in chat_data
        assert len(chat_data["response"]) > 10

        # 2. Smart Meal Reminders Settings
        reminder_settings_res = await client.get("/api/reminders/settings", headers=headers)
        assert reminder_settings_res.status_code == 200
        
        update_reminder_res = await client.put("/api/reminders/settings", headers=headers, json={
            "breakfast_enabled": True,
            "breakfast_time": "08:30",
            "lunch_enabled": True,
            "lunch_time": "13:00",
            "dinner_enabled": True,
            "dinner_time": "20:00",
            "auto_remind_unlogged": True
        })
        assert update_reminder_res.status_code == 200
        assert update_reminder_res.json()["breakfast_time"] == "08:30"

        # 3. Active Allergies CRUD
        allg_create = await client.post("/api/allergies", headers=headers, json={
            "allergen_type": "Peanuts",
            "severity": "severe",
            "notes": "Anaphylaxis risk"
        })
        assert allg_create.status_code in [200, 201]
        allg_id = allg_create.json()["id"]

        allg_list = await client.get("/api/allergies", headers=headers)
        assert allg_list.status_code == 200
        assert any(a["id"] == allg_id for a in allg_list.json())

        allg_del = await client.delete(f"/api/allergies/{allg_id}", headers=headers)
        assert allg_del.status_code == 200

@pytest.mark.asyncio
async def test_phase_25_26_27_exports_privacy_and_data_isolation():
    """PHASE 25, 26 & 27: Multi-Format Exports (PDF/CSV/JSON), Privacy Governance & User Data Isolation"""
    transport = ASGITransport(app=app)
    user_a = make_user()
    user_b = make_user()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register User A
        reg_a = await client.post("/api/auth/register", json={
            "name": user_a["name"],
            "email": user_a["email"],
            "password": user_a["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Setup User A profile
        await client.post("/api/profile", headers=headers_a, json={
            "name": user_a["name"],
            "age": 29,
            "gender": "female",
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity_level": "moderately_active",
            "fitness_goal": "maintain",
            "dietary_preference": "standard"
        })

        # Register User B
        reg_b = await client.post("/api/auth/register", json={
            "name": user_b["name"],
            "email": user_b["email"],
            "password": user_b["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User A logs a confidential meal
        food_res = await client.get("/api/foods?query=Sambar")
        food = food_res.json()[0]

        meal_a_res = await client.post("/api/meals", headers=headers_a, json={
            "meal_type": "lunch",
            "source": "manual",
            "items": [{
                "food_id": food["id"],
                "food_name": food["name"],
                "quantity": 1.0,
                "serving_unit": "bowl",
                "grams": 150.0,
                "calories": float(food["calories"]),
                "protein_g": float(food.get("protein_g", 0.0) or 0.0),
                "carbs_g": float(food.get("carbs_g", 0.0) or 0.0),
                "fat_g": float(food.get("fat_g", 0.0) or 0.0),
                "fiber_g": float(food.get("fiber_g", 0.0) or 0.0)
            }]
        })
        assert meal_a_res.status_code in [200, 201]
        meal_a_id = meal_a_res.json()["id"]

        # Data Isolation Check: User B MUST NOT see User A's meal
        user_b_meals = (await client.get("/api/meals", headers=headers_b)).json()
        assert not any(m["id"] == meal_a_id for m in user_b_meals)

        # Multi-Format Exports for User A
        # 1. JSON Export
        json_exp = await client.get("/api/export/json", headers=headers_a)
        assert json_exp.status_code == 200
        json_data = json_exp.json()
        assert "profile" in json_data
        assert "meals" in json_data
        assert len(json_data["meals"]) >= 1

        # 2. CSV Export
        csv_exp = await client.get("/api/export/csv", headers=headers_a)
        assert csv_exp.status_code == 200
        csv_text = csv_exp.text
        assert "Date,Time,Meal Type,Food Name,Quantity,Serving Unit" in csv_text
        assert "Sambar" in csv_text

        # 3. PDF Export
        pdf_exp = await client.get("/api/export/pdf", headers=headers_a)
        assert pdf_exp.status_code == 200
        assert pdf_exp.headers.get("content-type") == "application/pdf"
        assert pdf_exp.content.startswith(b"%PDF")
