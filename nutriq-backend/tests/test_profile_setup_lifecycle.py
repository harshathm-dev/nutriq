import pytest
import uuid
import asyncio
from httpx import AsyncClient, ASGITransport, Response
from unittest.mock import patch
from sqlalchemy import select

from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.models.profile import UserProfile
from app.models.goal import Goal


@pytest.mark.asyncio
async def test_scenario_1_complete_profile_setup_and_concurrent_dashboard_refresh():
    """
    TEST 1:
    Create a new account, complete profile steps 1-3, and immediately trigger
    concurrent dashboard refresh requests (simulating React frontend's refreshAllData()).
    Must complete with 0 database closed errors.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        test_email = f"profile_user_{uuid.uuid4().hex[:8]}@example.com"
        password = "SecurePassword123!"

        # 1. Register User
        res_reg = await client.post("/api/auth/register", json={
            "email": test_email,
            "password": password,
            "name": "Alex Profile",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert res_reg.status_code == 201
        token = res_reg.json()["access_token"]
        user_id = res_reg.json()["user_id"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Complete Profile Setup (Step 1, 2, 3)
        res_prof = await client.post("/api/profile", headers=headers, json={
            "name": "Alex Profile",
            "age": 28,
            "gender": "male",
            "height_cm": 178.0,
            "weight_kg": 75.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "standard"
        })
        assert res_prof.status_code == 201
        prof_data = res_prof.json()
        assert prof_data["name"] == "Alex Profile"
        assert prof_data["weight_kg"] == 75.0
        assert prof_data["fitness_goal"] == "weight_loss"

        # 3. Simulate React frontend refreshAllData() concurrent requests
        results = await asyncio.gather(
            client.get("/api/profile", headers=headers),
            client.get("/api/nutrition/targets", headers=headers),
            client.get("/api/analytics/daily", headers=headers),
            client.get("/api/meals/today", headers=headers),
            client.get("/api/daily-summary", headers=headers),
            client.get("/api/reminders/settings", headers=headers),
            client.get("/api/streak/status", headers=headers),
            return_exceptions=True
        )

        for res in results:
            assert not isinstance(res, Exception), f"Concurrent request raised exception: {res}"
            assert res.status_code == 200, f"Expected 200 but got {res.status_code}: {res.text}"

        # Verify nutrition targets were calculated scientifically
        targets_res = results[1]
        targets_data = targets_res.json()
        assert targets_data["calorie_target"] > 0
        assert targets_data["protein_g"] > 0
        assert targets_data["bmr"] > 0
        assert targets_data["tdee"] > 0


@pytest.mark.asyncio
async def test_scenario_2_google_user_profile_setup():
    """
    TEST 2:
    Login with Google -> Complete profile setup -> Access dashboard with 0 errors.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        google_email = f"google_profile_{uuid.uuid4().hex[:8]}@gmail.com"
        google_sub = f"gsub_prof_{uuid.uuid4().hex[:8]}"

        mock_tokeninfo_resp = Response(
            status_code=200,
            json={"email": google_email, "name": "Google Athlete", "sub": google_sub}
        )

        with patch("httpx.AsyncClient.get", return_value=mock_tokeninfo_resp):
            res_auth = await client.post("/api/auth/google", json={"credential": "mock_jwt"})
            assert res_auth.status_code == 200
            token = res_auth.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

        # Save Profile
        res_prof = await client.post("/api/profile", headers=headers, json={
            "name": "Google Athlete",
            "age": 25,
            "gender": "female",
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity_level": "very_active",
            "fitness_goal": "muscle_building",
            "dietary_preference": "vegetarian"
        })
        assert res_prof.status_code == 201

        # Fetch Targets
        res_targets = await client.get("/api/nutrition/targets", headers=headers)
        assert res_targets.status_code == 200
        targets = res_targets.json()
        assert targets["protein_g"] >= 60.0


@pytest.mark.asyncio
async def test_scenario_3_multi_user_profile_isolation():
    """
    TEST 3:
    Two users create independent profiles. User A's updates never overwrite or leak to User B.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User 1
        res1 = await client.post("/api/auth/register", json={
            "email": f"user1_{uuid.uuid4().hex[:8]}@example.com",
            "password": "Password123!",
            "name": "User One"
        })
        token1 = res1.json()["access_token"]

        # User 2
        res2 = await client.post("/api/auth/register", json={
            "email": f"user2_{uuid.uuid4().hex[:8]}@example.com",
            "password": "Password123!",
            "name": "User Two"
        })
        token2 = res2.json()["access_token"]

        # User 1 sets profile: 85kg
        await client.post("/api/profile", headers={"Authorization": f"Bearer {token1}"}, json={
            "name": "User One", "age": 30, "gender": "male", "height_cm": 180, "weight_kg": 85, "activity_level": "sedentary", "fitness_goal": "weight_loss"
        })

        # User 2 sets profile: 55kg
        await client.post("/api/profile", headers={"Authorization": f"Bearer {token2}"}, json={
            "name": "User Two", "age": 24, "gender": "female", "height_cm": 160, "weight_kg": 55, "activity_level": "lightly_active", "fitness_goal": "maintain"
        })

        # Fetch profile for User 1
        p1 = (await client.get("/api/profile", headers={"Authorization": f"Bearer {token1}"})).json()
        assert p1["weight_kg"] == 85.0
        assert p1["fitness_goal"] == "weight_loss"

        # Fetch profile for User 2
        p2 = (await client.get("/api/profile", headers={"Authorization": f"Bearer {token2}"})).json()
        assert p2["weight_kg"] == 55.0
        assert p2["fitness_goal"] == "maintain"
