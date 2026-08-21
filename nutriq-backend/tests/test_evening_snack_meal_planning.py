import pytest
import json
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.utils.date_utils import get_today_local

@pytest.fixture
def unique_email():
    return f"snack_tester_{uuid.uuid4().hex[:8]}@example.com"

async def register_and_setup_user(
    client: AsyncClient,
    email: str,
    fitness_goal: str = "weight_loss",
    dietary_pref: str = "standard",
    allergies: list = None
):
    # 1. Register
    reg_res = await client.post("/api/auth/register", json={
        "name": "Snack Planner User",
        "email": email,
        "password": "Password123!",
        "terms_accepted": True,
        "ai_consent_accepted": True
    })
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Setup Profile
    await client.post("/api/profile", headers=headers, json={
        "name": "Snack Planner User",
        "age": 29,
        "gender": "male",
        "height_cm": 178.0,
        "weight_kg": 76.0,
        "activity_level": "moderately_active",
        "fitness_goal": fitness_goal,
        "dietary_preference": dietary_pref
    })

    # 3. Setup Goal
    await client.post("/api/goals", headers=headers, json={
        "goal_type": fitness_goal,
        "current_weight_kg": 76.0,
        "target_weight_kg": 70.0 if fitness_goal == "weight_loss" else (82.0 if fitness_goal == "weight_gain" else 76.0),
        "desired_rate": 0.5
    })

    # 4. Setup Allergies if any
    if allergies:
        for allergen in allergies:
            await client.post("/api/allergies", headers=headers, json={
                "allergen_type": allergen,
                "severity": "severe",
                "notes": f"Allergic to {allergen}"
            })

    return headers

@pytest.mark.asyncio
async def test_3day_and_7day_plan_contains_all_four_slots(unique_email):
    """
    Test 1: 3-Day and 7-Day Plans contain Breakfast, Lunch, Evening Snack, Dinner on every day.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await register_and_setup_user(client, unique_email, fitness_goal="weight_loss", dietary_pref="standard")

        # 3-Day Plan
        res3 = await client.post("/api/ai/meal-plan", headers=headers, json={"days": 3})
        assert res3.status_code == 200
        plan3 = json.loads(res3.json()["plan_payload"])
        assert len(plan3["days"]) == 3

        for day_name, day_data in plan3["days"].items():
            assert "breakfast" in day_data, f"Missing breakfast in {day_name}"
            assert "lunch" in day_data, f"Missing lunch in {day_name}"
            assert "evening_snack" in day_data, f"Missing evening_snack in {day_name}"
            assert "dinner" in day_data, f"Missing dinner in {day_name}"
            assert "snack" in day_data, f"Missing snack alias in {day_name}"

            # Verify Evening Snack content
            snack = day_data["evening_snack"]
            assert snack["name"] and len(snack["name"].strip()) > 0
            assert snack["calories"] > 0
            assert snack["protein_g"] >= 0
            assert snack["carbs_g"] >= 0
            assert snack["fat_g"] >= 0

        # 7-Day Plan
        res7 = await client.post("/api/ai/meal-plan", headers=headers, json={"days": 7})
        assert res7.status_code == 200
        plan7 = json.loads(res7.json()["plan_payload"])
        assert len(plan7["days"]) == 7

        for day_name, day_data in plan7["days"].items():
            assert "evening_snack" in day_data
            assert day_data["evening_snack"]["calories"] > 0

@pytest.mark.asyncio
async def test_calorie_allocation_and_total_energy_calibration():
    """
    Test 2: Calorie allocation across 4 meals sums closely to user's daily target.
    """
    transport = ASGITransport(app=app)
    email = f"cal_budget_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await register_and_setup_user(client, email, fitness_goal="maintain")

        res = await client.post("/api/ai/meal-plan", headers=headers, json={"days": 3})
        assert res.status_code == 200
        plan = json.loads(res.json()["plan_payload"])
        target_cal = plan["daily_target_calories"]

        for day_name, day_data in plan["days"].items():
            b_cal = day_data["breakfast"]["calories"]
            l_cal = day_data["lunch"]["calories"]
            s_cal = day_data["evening_snack"]["calories"]
            d_cal = day_data["dinner"]["calories"]

            sum_cal = b_cal + l_cal + s_cal + d_cal
            summary_cal = day_data["daily_summary"]["total_calories"]

            # Sum matches daily summary
            assert abs(sum_cal - summary_cal) <= 5
            # Total matches target within small variance (<= 35 kcal)
            assert abs(sum_cal - target_cal) <= 35, f"{day_name} sum {sum_cal} differs too much from target {target_cal}"

            # Snack is approximately 10-20% of target calories
            assert 0.08 * target_cal <= s_cal <= 0.25 * target_cal, f"Snack calories {s_cal} outside expected allocation for {target_cal}"

@pytest.mark.asyncio
async def test_vegetarian_vegan_and_allergy_safety_in_evening_snack():
    """
    Test 3: Dietary safety and allergen restrictions strictly enforced in Evening Snack.
    """
    transport = ASGITransport(app=app)

    # 1. Vegan User (No dairy, no eggs, no meat)
    vegan_email = f"vegan_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await register_and_setup_user(client, vegan_email, dietary_pref="vegan")
        res = await client.post("/api/ai/meal-plan", headers=headers, json={"days": 5})
        assert res.status_code == 200
        plan = json.loads(res.json()["plan_payload"])

        forbidden_vegan = ["curd", "yogurt", "paneer", "milk", "butter", "ghee", "cheese", "egg", "chicken", "fish", "meat"]
        for day_name, day_data in plan["days"].items():
            snack_name = day_data["evening_snack"]["name"].lower()
            for bad_word in forbidden_vegan:
                assert bad_word not in snack_name, f"Forbidden non-vegan ingredient '{bad_word}' in vegan snack: {day_data['evening_snack']['name']}"

    # 2. Dairy Allergy User (No curd, paneer, milk, yogurt, buttermilk)
    dairy_allergy_email = f"dairy_allergy_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await register_and_setup_user(client, dairy_allergy_email, dietary_pref="vegetarian", allergies=["Dairy / Lactose"])
        res = await client.post("/api/ai/meal-plan", headers=headers, json={"days": 5})
        assert res.status_code == 200
        plan = json.loads(res.json()["plan_payload"])

        dairy_keywords = ["curd", "yogurt", "paneer", "milk", "butter", "ghee", "cheese", "dahi", "buttermilk", "lassi"]
        for day_name, day_data in plan["days"].items():
            snack_name = day_data["evening_snack"]["name"].lower()
            for bad_word in dairy_keywords:
                assert bad_word not in snack_name, f"Allergen '{bad_word}' found in dairy-allergic snack: {day_data['evening_snack']['name']}"

@pytest.mark.asyncio
async def test_regeneration_updates_evening_snack():
    """
    Test 4: Regenerating plan generates fresh non-repeating Evening Snacks.
    """
    transport = ASGITransport(app=app)
    email = f"regen_snack_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await register_and_setup_user(client, email, dietary_pref="standard")

        # Plan 1
        res1 = await client.post("/api/ai/meal-plan", headers=headers, json={"days": 3, "mode": "generate"})
        plan1 = json.loads(res1.json()["plan_payload"])
        plan1_id = res1.json()["id"]
        snacks_plan1 = [d["evening_snack"]["name"] for d in plan1["days"].values()]

        # Plan 2 (Regenerate)
        res2 = await client.post("/api/ai/meal-plan", headers=headers, json={
            "days": 3,
            "mode": "regenerate",
            "previous_plan_id": plan1_id,
            "regeneration_id": "regen_test_snack_unique_1"
        })
        plan2 = json.loads(res2.json()["plan_payload"])
        snacks_plan2 = [d["evening_snack"]["name"] for d in plan2["days"].values()]

        # Verify variety and change
        assert snacks_plan1 != snacks_plan2, f"Evening snacks did not change upon regeneration! {snacks_plan1} vs {snacks_plan2}"

@pytest.mark.asyncio
async def test_log_evening_snack_to_daily_summary():
    """
    Test 5: Logging generated Evening Snack records to journal with meal_type='snack' and updates Daily Summary.
    """
    transport = ASGITransport(app=app)
    email = f"log_snack_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await register_and_setup_user(client, email, dietary_pref="standard")

        # 1. Generate Plan
        res = await client.post("/api/ai/meal-plan", headers=headers, json={"days": 3})
        plan = json.loads(res.json()["plan_payload"])
        first_day_snack = list(plan["days"].values())[0]["evening_snack"]

        # 2. Log this snack to journal
        log_res = await client.post("/api/meals", headers=headers, json={
            "meal_type": "snack",
            "source": "meal_planner",
            "items": [
                {
                    "food_name": first_day_snack["name"],
                    "quantity": 1.0,
                    "serving_unit": "portion",
                    "grams": 100.0,
                    "calories": float(first_day_snack["calories"]),
                    "protein_g": float(first_day_snack["protein_g"]),
                    "carbs_g": float(first_day_snack["carbs_g"]),
                    "fat_g": float(first_day_snack["fat_g"]),
                    "fiber_g": float(first_day_snack.get("fiber_g", 2.0))
                }
            ]
        })
        assert log_res.status_code == 201

        # 3. Check Daily Summary
        today_str = get_today_local().isoformat()
        sum_res = await client.get(f"/api/daily-summary?date={today_str}", headers=headers)
        assert sum_res.status_code == 200
        sum_data = sum_res.json()

        # Evening Snack slot is recorded as logged
        assert sum_data["meals"]["snack"]["logged"] is True
        assert sum_data["meals"]["snack"]["status_label"] == "Logged"
        assert sum_data["meals"]["snack"]["total_calories"] == float(first_day_snack["calories"])
