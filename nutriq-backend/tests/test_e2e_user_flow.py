import pytest
import uuid
import httpx
from app.main import app

@pytest.mark.asyncio
async def test_nutriq_complete_user_flow():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # =========================================================================
        # TEST 1 & 13: Public Welcome & Health Endpoints
        # =========================================================================
        health_res = await client.get("/health")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "healthy"

        root_res = await client.get("/")
        assert root_res.status_code == 200

        # =========================================================================
        # TEST 2, 3, 4: User Registration with Name -> Incomplete Profile State
        # =========================================================================
        timestamp = uuid.uuid4().hex[:8]
        user_name = "Elena Rostova"
        user_email = f"elena_{timestamp}@example.com"
        user_pass = "Password123!"

        # Register
        reg_res = await client.post("/api/auth/register", json={
            "name": user_name,
            "email": user_email,
            "password": user_pass,
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg_res.status_code == 201
        reg_data = reg_res.json()
        token = reg_data["access_token"]
        assert token is not None
        auth_headers = {"Authorization": f"Bearer {token}"}

        # TEST 8 & 12: Before completing profile setup, profile is None (incomplete)
        prof_init_res = await client.get("/api/profile", headers=auth_headers)
        assert prof_init_res.status_code == 200
        assert prof_init_res.json() is None  # profile_complete = false -> MUST go to /profile-setup

        # =========================================================================
        # TEST 7: Login with Incomplete Profile User
        # =========================================================================
        login_incomplete_res = await client.post("/api/auth/login", json={
            "email": user_email,
            "password": user_pass
        })
        assert login_incomplete_res.status_code == 200
        inc_token = login_incomplete_res.json()["access_token"]
        inc_headers = {"Authorization": f"Bearer {inc_token}"}

        check_inc = await client.get("/api/profile", headers=inc_headers)
        assert check_inc.json() is None  # Still incomplete -> routes to /profile-setup

        # =========================================================================
        # TEST 4 & 5: Complete Profile Setup (/profile-setup)
        # =========================================================================
        prof_create_res = await client.post("/api/profile", headers=auth_headers, json={
            "name": user_name,
            "age": 27,
            "gender": "female",
            "height_cm": 168.0,
            "weight_kg": 60.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "standard",
            "food_preferences": "High protein breakfast"
        })
        assert prof_create_res.status_code == 201
        prof = prof_create_res.json()
        assert prof["name"] == "Elena Rostova"
        assert prof["age"] == 27
        assert prof["gender"] == "female"
        assert prof["height_cm"] == 168.0
        assert prof["weight_kg"] == 60.0
        assert prof["activity_level"] == "moderately_active"
        assert prof["fitness_goal"] == "weight_loss"

        # Create Goal
        goal_res = await client.post("/api/goals", headers=auth_headers, json={
            "goal_type": "weight_loss",
            "current_weight_kg": 60.0,
            "target_weight_kg": 55.0,
            "desired_rate": 0.5
        })
        assert goal_res.status_code == 201

        # Retrieve calculated targets
        targets_res = await client.get("/api/nutrition/targets", headers=auth_headers)
        assert targets_res.status_code == 200
        targets = targets_res.json()
        assert targets["target_calories"] > 0
        assert targets["bmr"] > 0
        assert targets["tdee"] > 0

        # =========================================================================
        # TEST 6 & 10: Returning User Login -> Complete Profile -> /dashboard
        # =========================================================================
        login_complete_res = await client.post("/api/auth/login", json={
            "email": user_email,
            "password": user_pass
        })
        assert login_complete_res.status_code == 200
        comp_token = login_complete_res.json()["access_token"]
        comp_headers = {"Authorization": f"Bearer {comp_token}"}

        prof_complete_check = await client.get("/api/profile", headers=comp_headers)
        assert prof_complete_check.status_code == 200
        completed_prof = prof_complete_check.json()
        assert completed_prof is not None
        # All required fields present
        assert completed_prof["name"] == user_name
        assert completed_prof["age"] == 27
        assert completed_prof["gender"] == "female"
        assert completed_prof["height_cm"] == 168.0
        assert completed_prof["weight_kg"] == 60.0
        assert completed_prof["activity_level"] == "moderately_active"
        assert completed_prof["fitness_goal"] == "weight_loss"
        # Deterministic check: All required fields exist -> profile_complete = true -> /dashboard

        # =========================================================================
        # TEST 11: Protected Route Guarding (Unauthorized requests)
        # =========================================================================
        unauth_prof = await client.get("/api/profile")
        assert unauth_prof.status_code == 401

        unauth_targets = await client.get("/api/nutrition/targets")
        assert unauth_targets.status_code == 401

        unauth_meals = await client.get("/api/meals")
        assert unauth_meals.status_code == 401

        # =========================================================================
        # TEST 12: Zero Fake Data Validation
        # =========================================================================
        assert completed_prof["name"] != "Fitness Enthusiast"
        assert completed_prof["name"] != "Test User"
        assert completed_prof["name"] != "User"
        assert completed_prof["name"] == "Elena Rostova"
