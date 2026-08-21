"""
Import and integrate NutriQ Indian Food Dataset (1,014 records)
into the existing NutriQ SQLite database safely and idempotently.
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

# Add backend root to path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND_DIR)

from app.data.dataset_part1 import RAW_CSV_PART1
from app.data.dataset_part2 import RAW_CSV_PART2
from app.data.dataset_part3 import RAW_CSV_PART3
from app.data.dataset_part4 import RAW_CSV_PART4

CSV_FILE_PATH = os.path.join(BACKEND_DIR, "app", "data", "NutriQ_Indian_Food_Dataset_Cleaned.csv")
DB_FILE_PATH = os.path.join(BACKEND_DIR, "nutriq.db")

CSV_HEADER = "food_id,Dish Name,Calories (kcal),Carbohydrates (g),Protein (g),Fats (g),Free Sugar (g),Fibre (g),Sodium (mg),Calcium (mg),Iron (mg),Vitamin C (mg),Folate (µg),source\n"


def build_full_csv_file():
    """Concatenate parts into a single verified CSV file."""
    os.makedirs(os.path.dirname(CSV_FILE_PATH), exist_ok=True)
    all_rows = []
    for part in [RAW_CSV_PART1, RAW_CSV_PART2, RAW_CSV_PART3, RAW_CSV_PART4]:
        for line in part.strip().split("\n"):
            line = line.strip()
            if line:
                all_rows.append(line)

    with open(CSV_FILE_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(CSV_HEADER)
        for row in all_rows:
            f.write(row + "\n")

    print(f"Generated clean CSV file at {CSV_FILE_PATH} with {len(all_rows)} data records.")
    return len(all_rows)


def backup_database():
    """Create a backup of the current database before modifying."""
    if not os.path.exists(DB_FILE_PATH):
        print(f"Warning: Database file {DB_FILE_PATH} does not exist yet.")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKEND_DIR, f"nutriq.db.backup_{timestamp}")
    shutil.copy2(DB_FILE_PATH, backup_path)
    # Also save standard backup
    shutil.copy2(DB_FILE_PATH, os.path.join(BACKEND_DIR, "nutriq.db.bak"))
    print(f"Database backed up successfully to: {backup_path}")
    return backup_path


def normalize_name(name: str) -> str:
    """Normalize food name for duplicate detection."""
    if not name:
        return ""
    # Unicode NFKC normalization
    s = unicodedata.normalize("NFKC", name).lower().strip()
    # Strip text in parentheses if secondary alias (keep base name)
    # e.g. "Hot tea (Garam Chai)" -> "hot tea", "Boiled egg (Ubla anda)" -> "boiled egg"
    base_name = re.sub(r"\(.*?\)", "", s).strip()
    # Remove special punctuation and extra spaces
    cleaned = re.sub(r"[^a-z0-9\s]", " ", base_name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned else re.sub(r"[^a-z0-9\s]", " ", s).strip()


def infer_category(dish_name: str) -> str:
    """Infer food category based on dish name keywords."""
    name = dish_name.lower()

    # Beverages
    if any(k in name for k in ["tea", "chai", "coffee", "lemonade", "drink", "cooler", "milkshake", "lassi", "canjee", "juice", "egg nog", "jal jeera", "gingo", "mintade", "coco pine", "kehwa"]):
        return "beverages"

    # Breakfast
    if any(k in name for k in ["dosa", "idli", "uthappam", "uttapam", "appam", "poha", "upma", "porridge", "daliya", "cheela", "chilla", "pongal", "thepla", "dhokla", "khaman", "pancake"]):
        if "dosa" in name:
            return "dosa"
        if "idli" in name:
            return "idli"
        if "uthappam" in name or "uttapam" in name:
            return "uthappam"
        return "breakfast"

    # Breads / Rotis
    if any(k in name for k in ["roti", "chapati", "parantha", "paratha", "poori", "puri", "naan", "bhatura", "bhature", "kulcha", "puranpoli", "phulka"]):
        return "roti/chapati"

    # Rice dishes
    if any(k in name for k in ["rice", "pulao", "biryani", "biriyani", "khichdi", "khitchdi", "bhaat", "chawal", "pulihora", "sadam", "anna"]):
        return "rice"

    # Legumes / Dals
    if any(k in name for k in ["dal", "chana", "channa", "rajma", "rajmah", "lobia", "moth", "masoor", "urad", "moong", "sambar", "sambhar", "rasam", "kootu", "pappu", "kadhi", "toor"]):
        return "legumes"

    # Dairy / Paneer
    if any(k in name for k in ["paneer", "curd", "dahi", "milk", "butter", "ghee", "raita", "khoa", "mawa", "chenna", "cheese"]):
        return "dairy"

    # Eggs
    if any(k in name for k in ["egg", "anda", "omelette", "omlet", "scrambled", "poached egg"]):
        return "eggs"

    # Meat / Poultry
    if any(k in name for k in ["chicken", "mutton", "lamb", "kebab", "seekh", "boti", "rogan josh", "roghan josh", "keema", "salami", "bacon", "meat", "reshmi", "shawarma", "sukka"]):
        return "meat"

    # Fish / Seafood
    if any(k in name for k in ["fish", "machli", "prawn", "prawns", "shrimp", "rohu", "catla", "katla"]):
        return "fish"

    # Sweets / Desserts
    if any(k in name for k in ["halwa", "kheer", "burfi", "barfi", "ladoo", "laddu", "kulfi", "ice cream", "custard", "pudding", "pastry", "cake", "biscuit", "cookies", "jalebi", "gulab jamun", "rasgulla", "rasmalai", "peda", "tart", "pie", "mousse", "souffle", "chikki", "phirni", "gunjia", "mal pua", "shahi tukre", "sweet", "gateau", "eclairs", "puffs", "flan"]):
        return "sweets"

    # Snacks & Street food
    if any(k in name for k in ["samosa", "pakora", "pakoda", "cutlet", "vada", "vadai", "sandwich", "roll", "burger", "chaat", "bhel", "sev puri", "pani puri", "golgappa", "kachori", "mathri", "tikki", "bonda", "patty", "patties", "toast", "papad", "sev", "khandvi", "handvo", "muthia", "vada pav", "pav bhaji", "misal pav", "dabeli", "ragda", "fries", "chips", "spring roll", "pasta", "noodles", "chowmein", "macroni", "macaroni", "spaghetti", "penne", "fettuccine", "lasagne"]):
        return "snacks"

    # Chutneys & Pickles / Condiments
    if any(k in name for k in ["chutney", "pickle", "achar", "podi", "thokku", "sauce", "dressing", "dip", "aspic", "saunth", "sonth", "pachadi", "avakaya", "gun powder"]):
        return "chutneys"

    # Vegetables
    return "vegetables"


def parse_csv_rows():
    """Read all rows from the dataset CSV."""
    records = []
    with open(CSV_FILE_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records


def run_migration():
    """Execute the safe database import."""
    print("=" * 60)
    print("NUTRIQ — INDIAN FOOD DATASET SAFE IMPORT PROCESS")
    print("=" * 60)

    # 1. Build and verify CSV file
    total_csv_records = build_full_csv_file()
    assert total_csv_records == 1014, f"Expected 1014 CSV records, got {total_csv_records}"

    # 2. Backup database
    backup_database()

    # 3. Connect to SQLite database
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()

    # Ensure tables exist
    cursor.execute("SELECT COUNT(*) FROM foods")
    initial_food_count = cursor.fetchone()[0]
    print(f"Existing food records in database before import: {initial_food_count}")

    # Fetch existing foods for duplicate & conflict detection
    cursor.execute("SELECT id, name, category, calories, protein_g, carbs_g, fat_g, fiber_g, sugar_g, sodium_mg FROM foods")
    existing_rows = cursor.fetchall()

    existing_foods_by_norm = {}
    existing_foods_by_exact = {}

    for row in existing_rows:
        fid, fname, fcat, fcal, fprot, fcarbs, ffat, ffib, fsug, fsod = row
        norm = normalize_name(fname)
        item_dict = {
            "id": fid,
            "name": fname,
            "category": fcat,
            "calories": fcal,
            "protein_g": fprot,
            "carbs_g": fcarbs,
            "fat_g": ffat,
            "fiber_g": ffib,
            "sugar_g": fsug,
            "sodium_mg": fsod,
        }
        existing_foods_by_norm[norm] = item_dict
        existing_foods_by_exact[fname.lower().strip()] = item_dict

    # 4. Parse CSV records
    csv_records = parse_csv_rows()
    print(f"Total CSV records parsed: {len(csv_records)}")

    duplicates_detected = 0
    duplicates_skipped = 0
    new_foods_inserted = 0
    nutrition_conflicts = []

    now_utc = datetime.now(timezone.utc).isoformat()

    foods_to_insert = []
    conversions_to_insert = []

    for row in csv_records:
        dish_name = row["Dish Name"].strip()
        norm_name = normalize_name(dish_name)
        exact_name = dish_name.lower().strip()

        try:
            cal = round(float(row["Calories (kcal)"]), 2)
            carbs = round(float(row["Carbohydrates (g)"]), 2)
            prot = round(float(row["Protein (g)"]), 2)
            fat = round(float(row["Fats (g)"]), 2)
            sugar = round(float(row["Free Sugar (g)"]), 2)
            fiber = round(float(row["Fibre (g)"]), 2)
            sodium = round(float(row["Sodium (mg)"]), 2)
        except ValueError as e:
            print(f"Skipping malformed row {dish_name}: {e}")
            continue

        # Check if already in database
        existing = existing_foods_by_exact.get(exact_name) or existing_foods_by_norm.get(norm_name)

        if existing:
            duplicates_detected += 1
            duplicates_skipped += 1

            # Check if there is a notable nutritional difference (> 15% delta)
            exist_cal = existing["calories"]
            if exist_cal > 0:
                diff_pct = abs(cal - exist_cal) / exist_cal * 100.0
                if diff_pct > 15.0:
                    nutrition_conflicts.append({
                        "dish_name": dish_name,
                        "existing_name": existing["name"],
                        "existing_calories": exist_cal,
                        "csv_calories": cal,
                        "diff_pct": round(diff_pct, 1),
                        "existing_macros": f"P:{existing['protein_g']}g C:{existing['carbs_g']}g F:{existing['fat_g']}g",
                        "csv_macros": f"P:{prot}g C:{carbs}g F:{fat}g",
                    })
            continue

        # Assign new food record
        new_id = str(uuid.uuid4())
        category = infer_category(dish_name)
        source = "Indian Food Nutrition Dataset"

        food_tuple = (
            new_id,
            dish_name,
            category,
            100.0,  # serving_size
            "g",    # unit
            cal,
            prot,
            carbs,
            fat,
            fiber,
            sugar,
            sodium,
            source,
            None,   # barcode
            now_utc # updated_at
        )
        foods_to_insert.append(food_tuple)

        # Standard 100g serving conversion
        conv_id = str(uuid.uuid4())
        conv_tuple = (
            conv_id,
            new_id,
            "100g",
            100.0,
            "g"
        )
        conversions_to_insert.append(conv_tuple)

        # Also register in existing lookup dicts to prevent intra-CSV duplicates
        new_item_dict = {
            "id": new_id,
            "name": dish_name,
            "category": category,
            "calories": cal,
            "protein_g": prot,
            "carbs_g": carbs,
            "fat_g": fat,
            "fiber_g": fiber,
            "sugar_g": sugar,
            "sodium_mg": sodium,
        }
        existing_foods_by_norm[norm_name] = new_item_dict
        existing_foods_by_exact[exact_name] = new_item_dict
        new_foods_inserted += 1

    # 5. Insert new foods and conversions into SQLite
    cursor.executemany("""
        INSERT INTO foods (
            id, name, category, serving_size, unit,
            calories, protein_g, carbs_g, fat_g, fiber_g,
            sugar_g, sodium_mg, source, barcode, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, foods_to_insert)

    cursor.executemany("""
        INSERT INTO serving_conversions (
            id, food_id, serving_label, grams, unit
        ) VALUES (?, ?, ?, ?, ?)
    """, conversions_to_insert)

    conn.commit()

    # 6. Verify final counts
    cursor.execute("SELECT COUNT(*) FROM foods")
    final_food_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM serving_conversions")
    final_conversion_count = cursor.fetchone()[0]

    conn.close()

    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"Existing food count before import : {initial_food_count}")
    print(f"Total CSV records parsed         : {total_csv_records}")
    print(f"Duplicates detected & skipped    : {duplicates_skipped}")
    print(f"New foods inserted               : {new_foods_inserted}")
    print(f"Nutrition conflicts identified   : {len(nutrition_conflicts)}")
    print(f"Final food count in database     : {final_food_count}")
    print(f"Final conversions in database    : {final_conversion_count}")
    print("=" * 60)

    if nutrition_conflicts:
        print("\nTop Nutrition Conflicts (Existing Curated IFCT vs Imported CSV):")
        for i, conflict in enumerate(nutrition_conflicts[:10], 1):
            print(f"  {i}. {conflict['dish_name']} (Existing: '{conflict['existing_name']}'): "
                  f"Existing {conflict['existing_calories']} kcal ({conflict['existing_macros']}) vs "
                  f"CSV {conflict['csv_calories']} kcal ({conflict['csv_macros']}) [diff: {conflict['diff_pct']}%]")

    return {
        "initial_food_count": initial_food_count,
        "total_csv_records": total_csv_records,
        "duplicates_skipped": duplicates_skipped,
        "new_foods_inserted": new_foods_inserted,
        "nutrition_conflicts_count": len(nutrition_conflicts),
        "nutrition_conflicts": nutrition_conflicts,
        "final_food_count": final_food_count,
    }


if __name__ == "__main__":
    run_migration()
