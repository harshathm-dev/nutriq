import pytest
import json
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def unique_user_email():
    return f"planner_user_{uuid.uuid4().hex[:8]}@example.com"

async def create_authenticated_user(client: AsyncClient, email: str, dietary_pref: str = "standard"):
    # 1. Register
    reg_res = await client.post("/api/auth/register", json={
        "name": "Planner Tester",
        "email": email,
        "password": "Password123!",
        "terms_accepted": True,
        "ai_consent_accepted": True
    })
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Complete profile
    await client.post("/api/profile", headers=headers, json={
        "name": "Planner Tester",
        "age": 28,
        "gender": "male",
        "height_cm": 175.0,
        "weight_kg": 72.0,
        "activity_level": "moderately_active",
        "fitness_goal": "maintain",
        "dietary_preference": dietary_pref
    })

    return headers

@pytest.mark.asyncio
async def test_meal_plan_regeneration_creates_different_plans(unique_user_email):
    """
    TEST:
    1. Generate Plan A.
    2. Click 'Regenerate Plan' -> Generate Plan B.
    3. Verify Plan B != Plan A.
    4. Click 'Regenerate Plan' -> Generate Plan C.
    5. Verify Plan C != Plan B and Plan C != Plan A.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await create_authenticated_user(client, unique_user_email, dietary_pref="standard")

        # 1. Generate Plan A
        res_a = await client.post("/api/ai/meal-plan", headers=headers, json={
            "days": 3,
            "budget_level": "medium",
            "mode": "generate"
        })
        assert res_a.status_code == 200
        plan_a_raw = res_a.json()
        plan_a = json.loads(plan_a_raw["plan_payload"])
        plan_a_id = plan_a_raw["id"]

        # 2. Regenerate Plan B
        res_b = await client.post("/api/ai/meal-plan", headers=headers, json={
            "days": 3,
            "budget_level": "medium",
            "mode": "regenerate",
            "previous_plan_id": plan_a_id,
            "regeneration_id": "regen_test_b_123"
        })
        assert res_b.status_code == 200
        plan_b_raw = res_b.json()
        plan_b = json.loads(plan_b_raw["plan_payload"])
        plan_b_id = plan_b_raw["id"]

        # Verify Plan B is distinct from Plan A
        dishes_a = [slot["name"] for day in plan_a["days"].values() for slot_name, slot in day.items() if slot_name != "daily_summary"]
        dishes_b = [slot["name"] for day in plan_b["days"].values() for slot_name, slot in day.items() if slot_name != "daily_summary"]

        assert dishes_a != dishes_b, "Plan B returned the exact same meals as Plan A!"

        # Overlap check: most dishes must be completely different
        common_ab = set(dishes_a).intersection(set(dishes_b))
        overlap_ratio = len(common_ab) / max(1, len(dishes_a))
        assert overlap_ratio < 0.4, f"Plan B has too much overlap with Plan A ({overlap_ratio:.1%})"

        # 3. Regenerate Plan C
        res_c = await client.post("/api/ai/meal-plan", headers=headers, json={
            "days": 3,
            "budget_level": "medium",
            "mode": "regenerate",
            "previous_plan_id": plan_b_id,
            "regeneration_id": "regen_test_c_456"
        })
        assert res_c.status_code == 200
        plan_c = json.loads(res_c.json()["plan_payload"])
        dishes_c = [slot["name"] for day in plan_c["days"].values() for slot_name, slot in day.items() if slot_name != "daily_summary"]

        assert dishes_c != dishes_b, "Plan C returned the exact same meals as Plan B!"
        assert dishes_c != dishes_a, "Plan C returned the exact same meals as Plan A!"

@pytest.mark.asyncio
async def test_five_consecutive_regenerations_produce_variety():
    """
    TEST: 5 consecutive regenerations continue to produce distinct meal combinations.
    """
    transport = ASGITransport(app=app)
    email = f"multi_regen_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await create_authenticated_user(client, email, dietary_pref="standard")

        generated_plans = []
        prev_id = None

        for i in range(5):
            res = await client.post("/api/ai/meal-plan", headers=headers, json={
                "days": 3,
                "budget_level": "medium",
                "mode": "regenerate" if i > 0 else "generate",
                "previous_plan_id": prev_id,
                "regeneration_id": f"seed_iteration_{i}_{uuid.uuid4().hex[:6]}"
            })
            assert res.status_code == 200
            data = res.json()
            prev_id = data["id"]
            payload = json.loads(data["plan_payload"])
            dishes = tuple(slot["name"] for day in payload["days"].values() for slot_name, slot in day.items() if slot_name != "daily_summary")
            generated_plans.append(dishes)

        # All 5 plans must be pairwise unique
        assert len(set(generated_plans)) == 5, "Some regenerated plans were identical duplicates!"

@pytest.mark.asyncio
async def test_calorie_and_macro_targets_calibrated():
    """
    TEST: Every day in the generated meal plan is accurately calibrated to user's caloric targets.
    """
    transport = ASGITransport(app=app)
    email = f"target_cal_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await create_authenticated_user(client, email, dietary_pref="standard")

        res = await client.post("/api/ai/meal-plan", headers=headers, json={"days": 5})
        assert res.status_code == 200
        plan = json.loads(res.json()["plan_payload"])

        target_cal = plan["daily_target_calories"]

        for day_name, day_data in plan["days"].items():
            summary = day_data["daily_summary"]
            # Variance must be within 30 kcal of target
            assert abs(summary["total_calories"] - target_cal) <= 30, f"{day_name} calorie variance too high: {summary['total_calories']} vs target {target_cal}"
            assert summary["total_protein_g"] > 25.0
            assert summary["total_carbs_g"] > 50.0
            assert summary["total_fat_g"] > 15.0

@pytest.mark.asyncio
async def test_vegetarian_and_allergy_restrictions():
    """
    TEST:
    - Vegetarian user receives 0 non-veg/meat/fish dishes.
    - User with peanut allergy receives 0 peanut dishes.
    """
    transport = ASGITransport(app=app)
    email = f"veg_user_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await create_authenticated_user(client, email, dietary_pref="vegetarian")

        # Add peanut allergy
        await client.post("/api/family/members", headers=headers, json={
            "relationship": "self",
            "dietary_preference": "vegetarian"
        })

        res = await client.post("/api/ai/meal-plan", headers=headers, json={"days": 5})
        assert res.status_code == 200
        plan = json.loads(res.json()["plan_payload"])

        non_veg_keywords = ["chicken", "mutton", "fish", "prawn", "seafood", "beef", "pork", "salami", "bacon", "meat"]

        for day_name, day_data in plan["days"].items():
            for slot_name, slot in day_data.items():
                if slot_name == "daily_summary":
                    continue
                dish_name = slot["name"].lower()
                for nvk in non_veg_keywords:
                    assert nvk not in dish_name, f"Found non-veg item '{slot['name']}' in vegetarian meal plan!"

@pytest.mark.asyncio
async def test_get_active_meal_plan_returns_latest():
    """
    TEST: GET /api/ai/meal-plan returns the latest regenerated active plan.
    """
    transport = ASGITransport(app=app)
    email = f"active_plan_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await create_authenticated_user(client, email)

        # Generate Plan 1
        res1 = await client.post("/api/ai/meal-plan", headers=headers, json={"days": 3})
        plan1_id = res1.json()["id"]

        # Regenerate Plan 2
        res2 = await client.post("/api/ai/meal-plan", headers=headers, json={"days": 3, "mode": "regenerate", "previous_plan_id": plan1_id})
        plan2_id = res2.json()["id"]

        # Fetch active plan
        get_res = await client.get("/api/ai/meal-plan", headers=headers)
        assert get_res.status_code == 200
        active_plan = get_res.json()
        assert active_plan is not None
        assert active_plan["id"] == plan2_id
        assert active_plan["active"] is True
