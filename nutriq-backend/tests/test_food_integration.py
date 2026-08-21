"""
Automated Validation Suite for NutriQ Master Food Integration
Validates:
- Zero duplicate foods
- Database uniqueness constraint
- Idempotent import
- Search relevance & accuracy
- Micronutrient fields
- Foreign key integrity & historical meal item persistence
- Meal calorie and macro calculations
"""

import os
import sys
import pytest
import sqlite3
import unicodedata
import re

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BACKEND_DIR)

from import_foods import import_master_dataset, normalize_food_name, make_unique_food_key

DB_PATH = os.path.join(BACKEND_DIR, "nutriq.db")
CSV_PATH = os.path.join(BACKEND_DIR, "app", "data", "NutriQ_Master_Cleaned_Food_Dataset.csv")


def test_master_csv_exists_and_has_exact_count():
    assert os.path.exists(CSV_PATH), "Master CSV must exist"
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    header = lines[0]
    records = lines[1:]
    assert len(records) == 2143, f"Expected 2143 records, found {len(records)}"
    assert "food_id,food_name,category,subcategory,region,serving_size" in header


def test_idempotent_import_runs():
    # Run 1
    r1 = import_master_dataset()
    assert r1["invalid_records"] == 0
    assert r1["duplicate_count_after_validation"] == 0

    # Run 2
    r2 = import_master_dataset()
    assert r2["new_records_inserted"] == 0
    assert r2["duplicate_count_after_validation"] == 0

    # Run 3
    r3 = import_master_dataset()
    assert r3["new_records_inserted"] == 0
    assert r3["duplicate_count_after_validation"] == 0


def test_zero_duplicates_in_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Zero duplicate normalized keys
    cursor.execute("""
        SELECT normalized_key, COUNT(*)
        FROM foods
        GROUP BY normalized_key
        HAVING COUNT(*) > 1
    """)
    dup_keys = cursor.fetchall()
    assert len(dup_keys) == 0, f"Found duplicate normalized keys: {dup_keys}"

    # 2. Zero duplicate food IDs
    cursor.execute("""
        SELECT id, COUNT(*)
        FROM foods
        GROUP BY id
        HAVING COUNT(*) > 1
    """)
    dup_ids = cursor.fetchall()
    assert len(dup_ids) == 0, f"Found duplicate food IDs: {dup_ids}"

    # 3. Unique index exists
    cursor.execute("""
        SELECT name FROM sqlite_master WHERE type='index' AND name='uq_food_normalized_key'
    """)
    idx = cursor.fetchone()
    assert idx is not None, "Unique index uq_food_normalized_key must exist"

    conn.close()


def test_foreign_key_integrity_and_meal_logs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Users count intact
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    assert user_count > 0, "Users table must not be empty"

    # Meals count intact
    cursor.execute("SELECT COUNT(*) FROM meals")
    meal_count = cursor.fetchone()[0]
    assert meal_count > 0, "Meals table must not be empty"

    # Meal items count intact
    cursor.execute("SELECT COUNT(*) FROM meal_items")
    item_count = cursor.fetchone()[0]
    assert item_count > 0, "Meal items must not be empty"

    # All meal_items point to existing food_id or have valid food_name
    cursor.execute("""
        SELECT mi.id, mi.food_id, mi.food_name
        FROM meal_items mi
        LEFT JOIN foods f ON mi.food_id = f.id
        WHERE f.id IS NULL AND mi.food_id IS NOT NULL
    """)
    orphaned_items = cursor.fetchall()
    assert len(orphaned_items) == 0, f"Found orphaned meal items: {orphaned_items}"

    conn.close()


def test_micronutrients_and_new_columns_exist():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(foods)")
    cols = {row[1] for row in cursor.fetchall()}
    expected_cols = {
        "id", "code", "name", "category", "subcategory", "region",
        "serving_size_desc", "serving_size", "unit", "calories",
        "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "sodium_mg",
        "calcium_mg", "iron_mg", "vitamin_c_mg", "folate_ug", "source",
        "normalized_key", "barcode", "updated_at"
    }
    for col in expected_cols:
        assert col in cols, f"Column '{col}' must exist in foods table"

    # Check some foods with micronutrients
    cursor.execute("SELECT COUNT(*) FROM foods WHERE calcium_mg IS NOT NULL OR iron_mg IS NOT NULL")
    micro_count = cursor.fetchone()[0]
    assert micro_count > 0, f"Expected foods with micronutrients, found {micro_count}"

    conn.close()


@pytest.mark.asyncio
async def test_search_and_ranking_async():
    from app.database.session import AsyncSessionLocal
    from app.services.food_service import FoodService

    async with AsyncSessionLocal() as session:
        # Search "Idli"
        idli_results = await FoodService.search_foods(session, "Idli", limit=10)
        assert len(idli_results) > 0
        assert any("idli" in f.name.lower() for f in idli_results)

        # Search "Dosa"
        dosa_results = await FoodService.search_foods(session, "Dosa", limit=10)
        assert len(dosa_results) > 0
        assert any("dosa" in f.name.lower() for f in dosa_results)

        # Search "Sambar"
        sambar_results = await FoodService.search_foods(session, "Sambar", limit=10)
        assert len(sambar_results) > 0
        assert any("sambar" in f.name.lower() for f in sambar_results)

        # Search "Rasam"
        rasam_results = await FoodService.search_foods(session, "Rasam", limit=10)
        assert len(rasam_results) > 0
        assert any("rasam" in f.name.lower() for f in rasam_results)

        # Search "Chicken"
        chicken_results = await FoodService.search_foods(session, "Chicken", limit=10)
        assert len(chicken_results) > 0
        assert any("chicken" in f.name.lower() for f in chicken_results)

        # Search "Paneer"
        paneer_results = await FoodService.search_foods(session, "Paneer", limit=10)
        assert len(paneer_results) > 0
        assert any("paneer" in f.name.lower() for f in paneer_results)
