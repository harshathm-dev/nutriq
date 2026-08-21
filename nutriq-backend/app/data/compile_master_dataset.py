"""
Compiles all dataset parts into NutriQ_Master_Cleaned_Food_Dataset.csv
Total expected records: 2,143 (1,014 Indian Food + 1,129 South Indian Food)
"""

import os
import sys
import csv
import io

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND_DIR)

from app.data.dataset_part1 import RAW_CSV_PART1
from app.data.dataset_part2 import RAW_CSV_PART2
from app.data.dataset_part3 import RAW_CSV_PART3
from app.data.dataset_part4 import RAW_CSV_PART4

from app.data.sif_dataset_part1 import RAW_SIF_PART1
from app.data.sif_dataset_part2 import RAW_SIF_PART2
from app.data.sif_dataset_part3 import RAW_SIF_PART3
from app.data.sif_dataset_part4 import RAW_SIF_PART4
from app.data.sif_dataset_part5 import RAW_SIF_PART5

MASTER_CSV_PATH = os.path.join(BACKEND_DIR, "app", "data", "NutriQ_Master_Cleaned_Food_Dataset.csv")
ROOT_CSV_PATH = os.path.join(os.path.abspath(os.path.join(BACKEND_DIR, "..")), "NutriQ_Master_Cleaned_Food_Dataset.csv")

CSV_HEADER = "food_id,food_name,category,subcategory,region,serving_size,calories_kcal,protein_g,carbohydrates_g,fat_g,fiber_g,free_sugar_g,sodium_mg,calcium_mg,iron_mg,vitamin_c_mg,folate_ug,source\n"

def compile_master_dataset():
    # 1. Gather IND lines
    ind_lines = []
    for part in [RAW_CSV_PART1, RAW_CSV_PART2, RAW_CSV_PART3, RAW_CSV_PART4]:
        for line in part.strip().split("\n"):
            line = line.strip()
            if line:
                ind_lines.append(line)

    # Convert old format of IND dataset into the new standard master format if needed
    # Header format: food_id,food_name,category,subcategory,region,serving_size,calories_kcal,protein_g,carbohydrates_g,fat_g,fiber_g,free_sugar_g,sodium_mg,calcium_mg,iron_mg,vitamin_c_mg,folate_ug,source
    standardized_ind_rows = []
    for line in ind_lines:
        reader = list(csv.reader(io.StringIO(line)))
        if not reader:
            continue
        row = reader[0]
        # In old parts: food_id,Dish Name,Calories (kcal),Carbohydrates (g),Protein (g),Fats (g),Free Sugar (g),Fibre (g),Sodium (mg),Calcium (mg),Iron (mg),Vitamin C (mg),Folate (µg),source
        food_id = row[0].strip()
        food_name = row[1].strip()
        cal = row[2].strip()
        carbs = row[3].strip()
        prot = row[4].strip()
        fat = row[5].strip()
        sugar = row[6].strip() if len(row) > 6 else ""
        fiber = row[7].strip() if len(row) > 7 else ""
        sodium = row[8].strip() if len(row) > 8 else ""
        calcium = row[9].strip() if len(row) > 9 else ""
        iron = row[10].strip() if len(row) > 10 else ""
        vit_c = row[11].strip() if len(row) > 11 else ""
        folate = row[12].strip() if len(row) > 12 else ""
        source = row[13].strip() if len(row) > 13 and row[13].strip() else "Existing NutriQ dataset"

        out_row = [
            food_id,
            food_name,
            "Indian Food",
            "",
            "India",
            "Source basis not specified",
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
            source
        ]
        buf = io.StringIO()
        csv.writer(buf, lineterminator="").writerow(out_row)
        standardized_ind_rows.append(buf.getvalue())

    # 2. Gather SIF lines
    sif_lines = []
    for part in [RAW_SIF_PART1, RAW_SIF_PART2, RAW_SIF_PART3, RAW_SIF_PART4, RAW_SIF_PART5]:
        for line in part.strip().split("\n"):
            line = line.strip()
            if line:
                sif_lines.append(line)

    all_rows = standardized_ind_rows + sif_lines

    # Write to app/data and root
    with open(MASTER_CSV_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(CSV_HEADER)
        for row in all_rows:
            f.write(row + "\n")

    with open(ROOT_CSV_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(CSV_HEADER)
        for row in all_rows:
            f.write(row + "\n")

    print(f"Master CSV generated successfully!")
    print(f"  IND records: {len(standardized_ind_rows)}")
    print(f"  SIF records: {len(sif_lines)}")
    print(f"  Total records: {len(all_rows)}")
    print(f"  App data file: {MASTER_CSV_PATH}")
    print(f"  Root file:     {ROOT_CSV_PATH}")
    return len(all_rows)

if __name__ == "__main__":
    compile_master_dataset()
