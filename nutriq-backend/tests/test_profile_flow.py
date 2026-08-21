import pytest
import uuid
import httpx
from app.main import app

@pytest.mark.asyncio
async def test_complete_onboarding_and_profile_flow():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        # 1. Register new user with name
        reg_res = await client.post("/api/auth/register", json={
            "name": "Sarah Connor",
            "email": unique_email,
            "password": "StrongPassword123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg_res.status_code == 201
        data = reg_res.json()
        token = data["access_token"]
        assert token is not None
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get profile before creation -> returns None / null
        get_init = await client.get("/api/profile", headers=headers)
        assert get_init.status_code == 200
        assert get_init.json() is None

        # 3. Login with the user before completing profile
        login_res = await client.post("/api/auth/login", json={
            "email": unique_email,
            "password": "StrongPassword123!"
        })
        assert login_res.status_code == 200
        login_token = login_res.json()["access_token"]
        login_headers = {"Authorization": f"Bearer {login_token}"}

        login_profile_res = await client.get("/api/profile", headers=login_headers)
        assert login_profile_res.status_code == 200
        assert login_profile_res.json() is None

        # 4. Create profile with full onboarding data
        prof_res = await client.post("/api/profile", headers=headers, json={
            "name": "Sarah Connor",
            "age": 28,
            "gender": "female",
            "height_cm": 168.0,
            "weight_kg": 62.0,
            "activity_level": "very_active",
            "fitness_goal": "muscle_building",
            "dietary_preference": "standard",
            "food_preferences": "High protein meals"
        })
        assert prof_res.status_code == 201
        prof_data = prof_res.json()
        assert prof_data["name"] == "Sarah Connor"
        assert prof_data["age"] == 28
        assert prof_data["weight_kg"] == 62.0
        assert prof_data["height_cm"] == 168.0
        assert prof_data["activity_level"] == "very_active"
        assert prof_data["fitness_goal"] == "muscle_building"

        # 5. Create Goal
        goal_res = await client.post("/api/goals", headers=headers, json={
            "goal_type": "muscle_building",
            "current_weight_kg": 62.0,
            "target_weight_kg": 65.0,
            "desired_rate": 0.25
        })
        assert goal_res.status_code == 201
        goal_data = goal_res.json()
        assert goal_data["goal_type"] == "muscle_building"
        assert goal_data["active"] is True

        # 6. Add Allergy
        allg_res = await client.post("/api/allergies", headers=headers, json={
            "allergen_type": "Shellfish",
            "severity": "moderate",
            "notes": "Recorded during profile setup"
        })
        assert allg_res.status_code == 201
        allg_data = allg_res.json()
        assert allg_data["allergen_type"] == "Shellfish"

        # 7. Retrieve Targets
        targets_res = await client.get("/api/nutrition/targets", headers=headers)
        assert targets_res.status_code == 200
        targets = targets_res.json()
        assert targets["bmr"] > 0
        assert targets["tdee"] > 0
        assert targets["target_calories"] > 0
        assert targets["protein_g"] > 0

        # 8. Test returning user login with complete profile
        ret_login = await client.post("/api/auth/login", json={
            "email": unique_email,
            "password": "StrongPassword123!"
        })
        assert ret_login.status_code == 200
        ret_token = ret_login.json()["access_token"]
        ret_headers = {"Authorization": f"Bearer {ret_token}"}

        ret_prof_res = await client.get("/api/profile", headers=ret_headers)
        assert ret_prof_res.status_code == 200
        ret_prof = ret_prof_res.json()
        assert ret_prof is not None
        assert ret_prof["name"] == "Sarah Connor"
        assert ret_prof["age"] == 28
        assert ret_prof["gender"] == "female"
        assert ret_prof["height_cm"] == 168.0
        assert ret_prof["weight_kg"] == 62.0
        assert ret_prof["activity_level"] == "very_active"
        assert ret_prof["fitness_goal"] == "muscle_building"

        # 9. Test Invalid Input on profile creation
        bad_res = await client.post("/api/profile", headers=headers, json={
            "name": "Invalid User",
            "age": 4, # Less than min age 10
            "gender": "female",
            "height_cm": 168.0,
            "weight_kg": 62.0
        })
        assert bad_res.status_code == 422
