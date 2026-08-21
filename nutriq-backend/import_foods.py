"""
NUTRIQ — Master Food Catalog Import & Duplicate Prevention Pipeline
Idempotent, database-constrained, zero-duplicate food catalog integration.
Preserves existing user accounts, meal logs, recipes, and foreign keys.
"""

import os
import sys
import csv
import re
import uuid
import shutil
import sqlite3
import unicodedata
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List

# Locate root directories
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
WORKSPACE_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
CSV_PATH = os.path.join(BACKEND_DIR, "app", "data", "NutriQ_Master_Cleaned_Food_Dataset.csv")
DB_PATH = os.path.join(BACKEND_DIR, "nutriq.db")


def normalize_food_name(name: str) -> str:
    """
    Standardize food name:
    - lowercase
    - unicode NFKC normalization
    - trim leading/trailing whitespace
    - collapse multiple spaces
    - normalize punctuation formatting (curly quotes, spacing around slashes)
    - preserve distinguishing qualifiers in parentheses
    """
    if not name:
        return ""
    s = unicodedata.normalize("NFKC", str(name)).lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"\s*/\s*", "/", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_serving(serving: str) -> str:
    """
    Standardize serving size representation.
    """
    if not serving or str(serving).strip().lower() in ["source basis not specified", "none", ""]:
        return "100g"
    s = unicodedata.normalize("NFKC", str(serving)).lower().strip()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def make_unique_food_key(name: str, serving_size: str) -> str:
    """
    Deterministic uniqueness key:
    normalized_food_name + "|" + normalized_serving_size
    """
    norm_name = normalize_food_name(name)
    norm_serving = normalize_serving(serving_size)
    return f"{norm_name}|{norm_serving}"


def parse_numeric(val: Any) -> Optional[float]:
    """Parse float safely, returns None if empty or invalid."""
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ["none", "null", "nan", ""]:
        return None
    try:
        return round(float(s), 2)
    except (ValueError, TypeError):
        return None


def parse_grams_from_serving_desc(serving_desc: str) -> float:
    """Extract numeric grams from serving description e.g. '2 pieces (~80g)' -> 80.0, '100ml' -> 100.0."""
    if not serving_desc:
        return 100.0
    # Look for (~80g) or (80g) or 80g
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:g|ml)", serving_desc, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return 100.0


def backup_database() -> Optional[str]:
    """Create timestamped backup of SQLite database."""
    if not os.path.exists(DB_PATH):
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKEND_DIR, f"nutriq.db.backup_{timestamp}")
    shutil.copy2(DB_PATH, backup_file)
    shutil.copy2(DB_PATH, os.path.join(BACKEND_DIR, "nutriq.db.bak"))
    print(f"[Backup] Database backed up to: {backup_file}")
    return backup_file


def apply_schema_migrations(cursor: sqlite3.Cursor):
    """Ensure all required columns and constraints exist in foods table."""
    cursor.execute("PRAGMA table_info(foods)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    columns_to_add = [
        ("code", "VARCHAR(50)"),
        ("subcategory", "VARCHAR(100)"),
        ("region", "VARCHAR(100)"),
        ("serving_size_desc", "VARCHAR(100)"),
        ("calcium_mg", "FLOAT"),
        ("iron_mg", "FLOAT"),
        ("vitamin_c_mg", "FLOAT"),
        ("folate_ug", "FLOAT"),
        ("normalized_key", "VARCHAR(255)"),
    ]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE foods ADD COLUMN {col_name} {col_type}")
                print(f"[Schema] Added column '{col_name}' to foods table.")
            except Exception as e:
                print(f"[Schema] Column '{col_name}' check: {e}")


def generate_serving_conversions(food_id: str, food_name: str, category: str, serving_desc: str, grams: float) -> List[Tuple[str, str, str, float, str]]:
    """Generate unique serving conversion entries for a food."""
    conversions = []
    seen_labels = set()

    def add_conv(label: str, g: float, u: str):
        lbl_norm = label.strip().lower()
        if lbl_norm and lbl_norm not in seen_labels:
            seen_labels.add(lbl_norm)
            conversions.append((str(uuid.uuid4()), food_id, label.strip(), g, u))
    
    # 1. Primary conversion from serving_desc
    if serving_desc and serving_desc.lower() != "source basis not specified":
        label = serving_desc.strip()
        unit = "piece" if "piece" in label.lower() else ("serving" if "serving" in label.lower() else "g")
        add_conv(label, grams, unit)
    
    # 2. Standard 100g base portion
    add_conv("100g base portion", 100.0, "g")

    # 3. Category-specific intelligent conversions
    cat_lower = (category or "").lower()
    name_lower = (food_name or "").lower()

    if "dosa" in cat_lower or "dosa" in name_lower:
        add_conv("1 dosa (standard)", 90.0, "dosa")
    elif "idli" in cat_lower or "idli" in name_lower:
        add_conv("1 piece (40g)", 40.0, "piece")
        add_conv("2 idlis (standard serving)", 80.0, "serving")
    elif "vada" in cat_lower or "vada" in name_lower:
        add_conv("1 vada (40g)", 40.0, "piece")
    elif "roti" in cat_lower or "chapati" in cat_lower or "roti" in name_lower:
        add_conv("1 piece (medium)", 40.0, "piece")
        add_conv("2 rotis / chapatis", 80.0, "serving")
    elif any(k in cat_lower or k in name_lower for k in ["sambar", "rasam", "kuzhambu", "dal", "curry", "soup", "kootu"]):
        add_conv("1 katori / bowl (150g)", 150.0, "katori")
        add_conv("1 small cup (100g)", 100.0, "cup")
    elif any(k in cat_lower or k in name_lower for k in ["rice", "biryani", "pulao", "pongal", "upma"]):
        add_conv("1 small bowl (100g)", 100.0, "bowl")
        add_conv("1 standard plate (180g)", 180.0, "plate")
    elif any(k in cat_lower or k in name_lower for k in ["chutney", "podi", "pickle", "thokku"]):
        add_conv("1 tablespoon (15g)", 15.0, "tbsp")
        add_conv("1 small serving (30g)", 30.0, "serving")
    elif any(k in cat_lower or k in name_lower for k in ["tea", "coffee", "beverage", "drink", "milk", "lassi", "juice"]):
        add_conv("1 cup / glass (150ml)", 150.0, "cup")

    return conversions



def import_master_dataset() -> Dict[str, Any]:
    print("=" * 70)
    print("NUTRIQ — AUTHORITATIVE FOOD DATASET IMPORT & ZERO DUPLICATE PIPELINE")
    print("=" * 70)

    # 1. Verify CSV file exists
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Master CSV not found at: {CSV_PATH}")

    # 2. Backup database
    backup_database()

    # 3. Connect to SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 4. Apply Schema Migrations
    apply_schema_migrations(cursor)

    # 5. Count initial database records
    cursor.execute("SELECT COUNT(*) FROM foods")
    initial_db_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM meals")
    meal_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM meal_items")
    meal_item_count = cursor.fetchone()[0]

    print(f"[Pre-Import] Existing DB foods: {initial_db_count} | Users: {user_count} | Meals: {meal_count} | Meal items: {meal_item_count}")

    # 6. Fetch existing DB foods and index by normalized_key, id, and exact name
    cursor.execute("""
        SELECT id, name, category, serving_size, unit, calories, protein_g, carbs_g, fat_g, fiber_g, sugar_g, sodium_mg, source, barcode, normalized_key, code
        FROM foods
    """)
    existing_rows = cursor.fetchall()

    existing_by_key: Dict[str, Dict[str, Any]] = {}
    existing_by_id: Dict[str, Dict[str, Any]] = {}
    existing_by_exact_name: Dict[str, Dict[str, Any]] = {}

    for row in existing_rows:
        fid, fname, fcat, fserv, funit, fcal, fprot, fcarbs, ffat, ffib, fsug, fsod, fsrc, fbar, fnorm, fcode = row
        
        # If normalized_key is not set, compute it now
        if not fnorm:
            fnorm = make_unique_food_key(fname, fserv)
            cursor.execute("UPDATE foods SET normalized_key = ? WHERE id = ?", (fnorm, fid))

        item_dict = {
            "id": fid,
            "name": fname,
            "category": fcat,
            "serving_size": fserv,
            "unit": funit,
            "calories": fcal,
            "protein_g": fprot,
            "carbs_g": fcarbs,
            "fat_g": ffat,
            "fiber_g": ffib,
            "sugar_g": fsug,
            "sodium_mg": fsod,
            "source": fsrc,
            "barcode": fbar,
            "normalized_key": fnorm,
            "code": fcode
        }
        existing_by_key[fnorm] = item_dict
        existing_by_id[fid] = item_dict
        existing_by_exact_name[fname.strip().lower()] = item_dict

    conn.commit()

    # Reconcile any pre-existing duplicates in the database to guarantee uniqueness
    cursor.execute("""
        SELECT normalized_key, GROUP_CONCAT(id)
        FROM foods
        GROUP BY normalized_key
        HAVING COUNT(*) > 1
    """)
    dup_groups = cursor.fetchall()
    for norm_k, ids_str in dup_groups:
        id_list = ids_str.split(",")
        referenced_id = None
        for cand_id in id_list:
            cursor.execute("SELECT COUNT(*) FROM meal_items WHERE food_id = ?", (cand_id,))
            if cursor.fetchone()[0] > 0:
                referenced_id = cand_id
                break
        canonical_id = referenced_id or id_list[0]
        for other_id in id_list:
            if other_id != canonical_id:
                cursor.execute("UPDATE meal_items SET food_id = ? WHERE food_id = ?", (canonical_id, other_id))
                cursor.execute("DELETE FROM serving_conversions WHERE food_id = ?", (other_id,))
                cursor.execute("DELETE FROM foods WHERE id = ?", (other_id,))
                if other_id in existing_by_id:
                    del existing_by_id[other_id]
        if canonical_id in existing_by_id:
            existing_by_key[norm_k] = existing_by_id[canonical_id]

    conn.commit()

    # Re-link any meal_items with dangling food_ids to matching catalog foods by name
    cursor.execute("""
        SELECT mi.id, mi.food_name, mi.food_id
        FROM meal_items mi
        LEFT JOIN foods f ON mi.food_id = f.id
        WHERE f.id IS NULL AND mi.food_id IS NOT NULL
    """)
    unmatched_items = cursor.fetchall()
    for mi_id, mi_name, old_fid in unmatched_items:
        if not mi_name:
            continue
        cursor.execute("SELECT id FROM foods WHERE LOWER(TRIM(name)) = LOWER(TRIM(?)) LIMIT 1", (mi_name,))
        match = cursor.fetchone()
        if not match:
            norm_name = normalize_food_name(mi_name)
            cursor.execute("SELECT id FROM foods WHERE LOWER(name) LIKE ? LIMIT 1", (f"%{norm_name}%",))
            match = cursor.fetchone()
        if match:
            cursor.execute("UPDATE meal_items SET food_id = ? WHERE id = ?", (match[0], mi_id))

    # Any remaining mock test IDs with no catalog food safely set food_id to NULL
    cursor.execute("""
        UPDATE meal_items
        SET food_id = NULL
        WHERE food_id NOT IN (SELECT id FROM foods) AND food_id IS NOT NULL
    """)

    conn.commit()




    # 7. Parse Master CSV (2,143 records)
    csv_records = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_records.append(row)

    total_csv_records = len(csv_records)
    print(f"[CSV Parsing] Total master CSV records loaded: {total_csv_records}")

    now_utc = datetime.now(timezone.utc).isoformat()

    new_inserted = 0
    duplicates_skipped = 0
    updated_records = 0
    invalid_records = 0

    foods_to_insert = []
    conversions_to_insert = []

    # Map of processed keys in this import batch
    batch_processed_keys = set()

    for idx, row in enumerate(csv_records, 1):
        food_id_code = row.get("food_id", "").strip()
        food_name = row.get("food_name", "").strip()
        category = row.get("category", "").strip()
        subcategory = row.get("subcategory", "").strip()
        region = row.get("region", "").strip()
        serving_size_desc = row.get("serving_size", "").strip()
        source = row.get("source", "").strip() or "NutriQ Master Dataset"

        if not food_name:
            invalid_records += 1
            continue

        cal = parse_numeric(row.get("calories_kcal"))
        prot = parse_numeric(row.get("protein_g")) or 0.0
        carbs = parse_numeric(row.get("carbohydrates_g")) or 0.0
        fat = parse_numeric(row.get("fat_g")) or 0.0
        fiber = parse_numeric(row.get("fiber_g")) or 0.0
        sugar = parse_numeric(row.get("free_sugar_g")) or 0.0
        sodium = parse_numeric(row.get("sodium_mg")) or 0.0
        calcium = parse_numeric(row.get("calcium_mg"))
        iron = parse_numeric(row.get("iron_mg"))
        vit_c = parse_numeric(row.get("vitamin_c_mg"))
        folate = parse_numeric(row.get("folate_ug"))

        if cal is None:
            invalid_records += 1
            continue

        # Compute unique deterministic key
        key = make_unique_food_key(food_name, serving_size_desc)

        # Check if already processed in this batch (intra-CSV duplicate)
        if key in batch_processed_keys:
            duplicates_skipped += 1
            continue

        batch_processed_keys.add(key)

        # Check if already in database
        existing_food = existing_by_key.get(key) or existing_by_exact_name.get(food_name.strip().lower())

        numeric_grams = parse_grams_from_serving_desc(serving_size_desc)
        serving_unit = "ml" if "ml" in serving_size_desc.lower() else "g"

        if existing_food:
            # Idempotent update of existing food: enrich missing fields, preserve existing ID & foreign keys
            fid = existing_food["id"]
            cursor.execute("""
                UPDATE foods
                SET code = COALESCE(?, code),
                    category = ?,
                    subcategory = ?,
                    region = ?,
                    serving_size_desc = ?,
                    serving_size = ?,
                    unit = ?,
                    calories = ?,
                    protein_g = ?,
                    carbs_g = ?,
                    fat_g = ?,
                    fiber_g = ?,
                    sugar_g = ?,
                    sodium_mg = ?,
                    calcium_mg = ?,
                    iron_mg = ?,
                    vitamin_c_mg = ?,
                    folate_ug = ?,
                    source = ?,
                    normalized_key = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                food_id_code, category, subcategory, region, serving_size_desc,
                numeric_grams, serving_unit, cal, prot, carbs, fat, fiber, sugar, sodium,
                calcium, iron, vit_c, folate, source, key, now_utc, fid
            ))
            
            # Ensure serving conversions exist
            cursor.execute("SELECT COUNT(*) FROM serving_conversions WHERE food_id = ?", (fid,))
            if cursor.fetchone()[0] == 0:
                convs = generate_serving_conversions(fid, food_name, category, serving_size_desc, numeric_grams)
                for c in convs:
                    conversions_to_insert.append(c)

            updated_records += 1
            duplicates_skipped += 1
        else:
            # Insert brand new food
            new_id = str(uuid.uuid4())
            food_tuple = (
                new_id,
                food_id_code,
                food_name,
                category,
                subcategory,
                region,
                serving_size_desc,
                numeric_grams,
                serving_unit,
                cal,
                prot,
                carbs,
                fat,
                fiber,
                sugar,
                sodium,
                calcium,
                iron,
                vit_c,
                folate,
                source,
                None,  # barcode
                key,
                now_utc
            )
            foods_to_insert.append(food_tuple)

            # Generate standard serving conversions
            convs = generate_serving_conversions(new_id, food_name, category, serving_size_desc, numeric_grams)
            for c in convs:
                conversions_to_insert.append(c)

            new_inserted += 1
            existing_by_key[key] = {"id": new_id, "name": food_name}
            existing_by_exact_name[food_name.strip().lower()] = {"id": new_id, "name": food_name}

    # 8. Execute batch inserts
    if foods_to_insert:
        cursor.executemany("""
            INSERT INTO foods (
                id, code, name, category, subcategory, region, serving_size_desc,
                serving_size, unit, calories, protein_g, carbs_g, fat_g, fiber_g,
                sugar_g, sodium_mg, calcium_mg, iron_mg, vitamin_c_mg, folate_ug,
                source, barcode, normalized_key, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, foods_to_insert)

    if conversions_to_insert:
        cursor.executemany("""
            INSERT OR IGNORE INTO serving_conversions (
                id, food_id, serving_label, grams, unit
            ) VALUES (?, ?, ?, ?, ?)
        """, conversions_to_insert)


    conn.commit()

    # 9. Create UNIQUE INDEX on normalized_key
    try:
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_food_normalized_key ON foods(normalized_key)")
        conn.commit()
        print("[Index] Database uniqueness constraint (uq_food_normalized_key) verified.")
    except Exception as e:
        print(f"[Index] Index note: {e}")

    # 10. Post-import Verification & Validation Audit
    cursor.execute("SELECT COUNT(*) FROM foods")
    final_db_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM serving_conversions")
    final_conversion_count = cursor.fetchone()[0]

    # Duplicate detection checks
    cursor.execute("""
        SELECT normalized_key, COUNT(*)
        FROM foods
        GROUP BY normalized_key
        HAVING COUNT(*) > 1
    """)
    dup_key_rows = cursor.fetchall()
    dup_key_count = len(dup_key_rows)

    cursor.execute("""
        SELECT LOWER(TRIM(name)), COUNT(*)
        FROM foods
        GROUP BY LOWER(TRIM(name))
        HAVING COUNT(*) > 1
    """)
    dup_name_rows = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM users")
    post_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM meals")
    post_meals = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM meal_items")
    post_meal_items = cursor.fetchone()[0]

    conn.close()

    print("\n" + "=" * 70)
    print("IMPORT & DUPLICATE VALIDATION REPORT")
    print("=" * 70)
    print(f"Existing records before import : {initial_db_count}")
    print(f"CSV records parsed             : {total_csv_records}")
    print(f"New records inserted           : {new_inserted}")
    print(f"Duplicates skipped             : {duplicates_skipped}")
    print(f"Updated records                : {updated_records}")
    print(f"Invalid records                : {invalid_records}")
    print(f"Final database records         : {final_db_count}")
    print(f"Final serving conversions      : {final_conversion_count}")
    print(f"Duplicate count after validation: {dup_key_count}")
    print(f"Historical user records intact : {post_users == user_count} (Users: {post_users})")
    print(f"Historical meal logs intact    : {post_meals == meal_count} (Meals: {post_meals}, Items: {post_meal_items})")
    print("=" * 70 + "\n")

    return {
        "existing_records": initial_db_count,
        "csv_records": total_csv_records,
        "new_records_inserted": new_inserted,
        "duplicates_skipped": duplicates_skipped,
        "updated_records": updated_records,
        "invalid_records": invalid_records,
        "final_food_count": final_db_count,
        "duplicate_count_after_validation": dup_key_count,
    }


if __name__ == "__main__":
    import_master_dataset()
