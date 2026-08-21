import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.food import Food
from sqlalchemy import select, func


@pytest.mark.asyncio
async def test_food_database_count():
    """Verify that the database has at least 1,000 foods loaded."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(Food.id)))
        total_foods = result.scalar_one()
        assert total_foods >= 1000, f"Expected >= 1000 foods in database, got {total_foods}"

    # Also test API food listing
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/foods?limit=100")
        assert res.status_code == 200
        foods = res.json()
        assert len(foods) == 100


@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected_keyword", [
    ("Dosa", "dosa"),
    ("Idli", "idli"),
    ("Sambar", "sambar"),
    ("Biryani", "biryani"),
    ("Pongal", "pongal"),
    ("Chapati", "chapati"),
    ("Rice", "rice"),
    ("Paneer", "paneer"),
    ("Chicken", "chicken"),
    ("Fish", "fish"),
])
async def test_search_required_dishes(query, expected_keyword):
    """Verify that all 10 required dish categories return verified foods."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/foods?query={query}&limit=50")
        assert res.status_code == 200
        results = res.json()
        assert len(results) > 0, f"Search for '{query}' returned 0 results"
        
        # Verify at least one result contains the keyword (case-insensitive)
        matches = [f for f in results if expected_keyword in f["name"].lower()]
        assert len(matches) > 0, f"No food matching keyword '{expected_keyword}' in results: {[f['name'] for f in results[:5]]}"
        
        # Verify nutrition values are numbers >= 0
        first_match = matches[0]
        assert first_match["calories"] >= 0
        assert first_match["serving_size"] == 100.0
        assert first_match["unit"] == "g"
        assert len(first_match["serving_conversions"]) >= 1


@pytest.mark.asyncio
async def test_meal_logging_with_quantity_scaling():
    """Verify registering a user, logging a newly imported food with a quantity multiplier (e.g. 2.5x)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register a test user
        email = f"foodtest_{uuid.uuid4().hex[:8]}@example.com"
        reg_res = await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "name": "Food Test User"
        })
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Search for Paneer Butter Masala
        search_res = await client.get("/api/foods?query=Paneer Butter Masala", headers=headers)
        assert search_res.status_code == 200
        search_data = search_res.json()
        assert len(search_data) > 0
        food_item = search_data[0]

        base_cal = food_item["calories"]
        base_prot = food_item["protein_g"]
        base_carbs = food_item["carbs_g"]
        base_fat = food_item["fat_g"]

        # 2. Log meal with 2.5 portions (250g)
        quantity = 2.5
        payload = {
            "meal_type": "lunch",
            "items": [
                {
                    "food_name": food_item["name"],
                    "quantity": quantity,
                    "serving_unit": "100g",
                    "grams": 100.0 * quantity,
                    "calories": round(base_cal * quantity, 2),
                    "protein_g": round(base_prot * quantity, 2),
                    "carbs_g": round(base_carbs * quantity, 2),
                    "fat_g": round(base_fat * quantity, 2),
                    "fiber_g": round(food_item["fiber_g"] * quantity, 2),
                    "sugar_g": round(food_item["sugar_g"] * quantity, 2),
                    "sodium_mg": round(food_item["sodium_mg"] * quantity, 2),
                    "source": food_item["source"]
                }
            ]
        }

        log_res = await client.post("/api/meals", json=payload, headers=headers)
        assert log_res.status_code == 201, f"Failed to log meal: {log_res.text}"
        logged_meal = log_res.json()
        totals = logged_meal["totals"]
        assert totals["calories"] == pytest.approx(base_cal * quantity, rel=1e-2)
        assert totals["protein_g"] == pytest.approx(base_prot * quantity, rel=1e-2)
        assert totals["carbs_g"] == pytest.approx(base_carbs * quantity, rel=1e-2)
        assert totals["fat_g"] == pytest.approx(base_fat * quantity, rel=1e-2)
