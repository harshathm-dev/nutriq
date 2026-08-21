import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app

def make_user(prefix="user"):
    uid = uuid.uuid4().hex[:8]
    return {
        "name": f"Test {prefix} {uid}",
        "email": f"{prefix}_{uid}@example.com",
        "password": "SecurePassword123!"
    }

@pytest.mark.asyncio
async def test_search_ranking_rice_prioritizes_direct_matches():
    """Test requirement 6: When searching 'rice', primary rice dishes are ranked before secondary mentions in parentheses (e.g. Adai)"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/foods?query=rice")
        assert res.status_code == 200
        foods = res.json()
        assert len(foods) > 0

        # Names of top results
        top_names = [f["name"].lower() for f in foods[:5]]
        
        # Check that top results have "rice" in their main name (e.g. "plain rice", "curd rice", "lemon rice", "rice pongal")
        assert any("rice" in name.split("(")[0] for name in top_names)

        # "Adai (Mixed Lentil & Rice Dosa)" should NOT be the very first result
        first_food = foods[0]["name"]
        assert not first_food.startswith("Adai"), f"Expected primary rice dish first, but got: {first_food}"

@pytest.mark.asyncio
async def test_search_case_insensitivity_and_whitespace():
    """Search is case-insensitive and whitespace tolerant"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res1 = await client.get("/api/foods?query=  RICE  ")
        assert res1.status_code == 200
        foods1 = res1.json()

        res2 = await client.get("/api/foods?query=rice")
        assert res2.status_code == 200
        foods2 = res2.json()

        assert len(foods1) == len(foods2)
        assert [f["id"] for f in foods1] == [f["id"] for f in foods2]

@pytest.mark.asyncio
async def test_empty_search_and_no_results():
    """Empty query returns catalog, unknown query returns empty list without error"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Empty query
        res_empty = await client.get("/api/foods")
        assert res_empty.status_code == 200
        assert len(res_empty.json()) > 0

        # Nonexistent query
        res_none = await client.get("/api/foods?query=xyznonexistentdish12345")
        assert res_none.status_code == 200
        assert res_none.json() == []

@pytest.mark.asyncio
async def test_explicit_meal_logging_workflow():
    """Test full search -> add portion -> save meal flow on backend"""
    user = make_user("search_flow")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/auth/register", json={
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Search for plain rice
        res_search = await client.get("/api/foods?query=rice", headers=headers)
        assert res_search.status_code == 200
        foods = res_search.json()
        
        # User explicitly chooses a food
        chosen_food = foods[0]

        # User explicitly adds 2 portions to Lunch
        meal_res = await client.post("/api/meals", headers=headers, json={
            "meal_type": "lunch",
            "items": [{
                "food_id": chosen_food["id"],
                "food_name": chosen_food["name"],
                "quantity": 2.0,
                "serving_unit": "portion",
                "grams": 200.0,
                "calories": chosen_food["calories"] * 2.0,
                "protein_g": chosen_food["protein_g"] * 2.0,
                "carbs_g": chosen_food["carbs_g"] * 2.0,
                "fat_g": chosen_food["fat_g"] * 2.0,
                "fiber_g": chosen_food.get("fiber_g", 0.0) * 2.0
            }]
        })
        assert meal_res.status_code in [200, 201]
        meal_data = meal_res.json()
        assert meal_data["meal_type"] == "lunch"
        assert len(meal_data["items"]) == 1
        assert meal_data["items"][0]["food_name"] == chosen_food["name"]
