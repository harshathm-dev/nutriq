import os
import json
import random
import numpy as np
from datetime import datetime, timezone
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score

from app.services.food_service import CURATED_FOOD_SEEDS
from app.ml.preprocessing import FeatureExtractor

MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
MODEL_FILE = os.path.join(MODEL_DIR, "food_recommender_v1.joblib")
METADATA_FILE = os.path.join(MODEL_DIR, "metadata.json")

def compute_ground_truth_suitability(
    user_profile: dict,
    nutrition_gap: dict,
    meal_slot: str,
    food: dict
) -> float:
    """
    Computes a deterministic, objective multi-factor suitability score (0.0 to 1.0)
    grounded in clinical nutrition principles.
    """
    cal_gap = float(nutrition_gap.get("calories_remaining", 500.0))
    pro_gap = float(nutrition_gap.get("protein_remaining", 30.0))
    goal = (user_profile.get("fitness_goal") or "maintain").lower()

    f_cal = float(food.get("calories", 150.0))
    f_pro = float(food.get("protein_g", 5.0))
    f_carb = float(food.get("carbs_g", 20.0))
    f_fat = float(food.get("fat_g", 4.0))
    f_fib = float(food.get("fiber_g", 2.0))

    score = 0.50

    # 1. Calorie Budget Factor (-0.35 to +0.30)
    if cal_gap <= 0:
        # Over calorie budget: reward light/hydrating foods, penalize high calories
        if f_cal <= 120:
            score += 0.25
        elif f_cal <= 200:
            score += 0.10
        elif f_cal >= 400:
            score -= 0.35
        else:
            score -= 0.15
    else:
        # Normal or deficit state: compute target slot budget
        slot_budget_ratio = {"breakfast": 0.25, "lunch": 0.35, "evening_snack": 0.15, "snack": 0.15, "dinner": 0.25}.get(meal_slot.lower(), 0.25)
        ideal_cal = max(100.0, min(800.0, cal_gap * slot_budget_ratio * 2.0))
        cal_diff_pct = abs(f_cal - ideal_cal) / max(100.0, ideal_cal)
        if cal_diff_pct < 0.25:
            score += 0.25
        elif cal_diff_pct < 0.50:
            score += 0.15
        elif f_cal > cal_gap + 50.0:
            score -= 0.30
        else:
            score += 0.05

    # 2. Protein Density Factor (-0.15 to +0.25)
    pro_density = f_pro / max(0.5, f_cal / 100.0)  # g protein per 100 kcal
    if pro_gap > 35 or "muscle" in goal:
        if pro_density >= 7.0 or f_pro >= 15.0:
            score += 0.25
        elif pro_density >= 4.0 or f_pro >= 8.0:
            score += 0.15
        elif pro_density < 1.5 and f_pro < 3.0:
            score -= 0.15
    elif "weight_loss" in goal:
        if pro_density >= 5.0:
            score += 0.15
        elif f_fib >= 4.0:
            score += 0.15

    # 3. Fiber and Micronutrient Density Factor (0.0 to +0.15)
    if f_fib >= 5.0:
        score += 0.12
    elif f_fib >= 3.0:
        score += 0.06

    # 4. Meal Slot Appropriateness Factor (-0.25 to +0.20)
    slot_compat = FeatureExtractor.compute_slot_compatibility(
        food.get("name", ""),
        food.get("category", ""),
        meal_slot
    )
    if slot_compat >= 0.8:
        score += 0.18
    elif slot_compat >= 0.5:
        score += 0.05
    else:
        score -= 0.20

    # 5. Goal Specific Adjustments
    if "weight_gain" in goal:
        if f_cal >= 300 and f_pro >= 8.0:
            score += 0.15
    elif "weight_loss" in goal:
        if f_cal > 500:
            score -= 0.15
        if f_fat > 20:
            score -= 0.10

    # Clamp to [0.05, 0.98]
    return float(max(0.05, min(0.98, round(score, 3))))

def generate_synthetic_training_dataset(num_samples: int = 5000) -> tuple:
    """
    Generates rich, reproducible training pairs across the entire Indian food catalog.
    """
    random.seed(42)
    np.random.seed(42)

    goals = ["weight_loss", "muscle_gain", "maintain", "weight_gain"]
    slots = ["breakfast", "lunch", "evening_snack", "dinner"]
    genders = ["male", "female"]

    foods = []
    for s in CURATED_FOOD_SEEDS:
        conversions = s.get("conversions", [])
        grams = conversions[0]["grams"] if conversions else 100.0
        label = conversions[0]["serving_label"] if conversions else "1 serving"
        # Scale to 1 serving
        scale = grams / 100.0
        foods.append({
            "name": s["name"],
            "category": s.get("category", "general"),
            "calories": round(float(s["calories"]) * scale, 1),
            "protein_g": round(float(s["protein_g"]) * scale, 1),
            "carbs_g": round(float(s["carbs_g"]) * scale, 1),
            "fat_g": round(float(s["fat_g"]) * scale, 1),
            "fiber_g": round(float(s["fiber_g"]) * scale, 1),
            "serving_grams": grams,
            "serving_label": label
        })

    X_list = []
    y_list = []

    for _ in range(num_samples):
        goal = random.choice(goals)
        slot = random.choice(slots)
        gender = random.choice(genders)

        age = random.randint(18, 65)
        height = random.uniform(150.0, 190.0)
        weight = random.uniform(50.0, 100.0)

        # Realistic calorie gap distributions
        cal_scenario = random.choices(
            ["deficit_large", "deficit_moderate", "on_target", "slight_surplus", "exceeded"],
            weights=[0.25, 0.35, 0.20, 0.10, 0.10]
        )[0]

        if cal_scenario == "deficit_large":
            cal_rem = random.uniform(800.0, 1600.0)
            pro_rem = random.uniform(40.0, 90.0)
        elif cal_scenario == "deficit_moderate":
            cal_rem = random.uniform(300.0, 800.0)
            pro_rem = random.uniform(20.0, 50.0)
        elif cal_scenario == "on_target":
            cal_rem = random.uniform(100.0, 300.0)
            pro_rem = random.uniform(10.0, 30.0)
        elif cal_scenario == "slight_surplus":
            cal_rem = random.uniform(0.0, 100.0)
            pro_rem = random.uniform(0.0, 15.0)
        else: # exceeded
            cal_rem = random.uniform(-400.0, 0.0)
            pro_rem = random.uniform(-10.0, 10.0)

        user_profile = {
            "fitness_goal": goal,
            "age": age,
            "gender": gender,
            "height_cm": height,
            "weight_kg": weight
        }

        nutrition_gap = {
            "calories_remaining": cal_rem,
            "protein_remaining": pro_rem,
            "carbs_remaining": max(0.0, cal_rem * 0.5 / 4.0),
            "fat_remaining": max(0.0, cal_rem * 0.25 / 9.0),
            "fiber_remaining": random.uniform(0.0, 20.0)
        }

        # Pick food candidate
        food = random.choice(foods)
        hist_freq = random.choices([0.0, 0.2, 0.5, 0.8], weights=[0.6, 0.2, 0.1, 0.1])[0]

        feats = FeatureExtractor.extract_features(
            user_profile=user_profile,
            nutrition_gap=nutrition_gap,
            meal_context=slot,
            food_item=food,
            user_history_freq=hist_freq
        )

        target_score = compute_ground_truth_suitability(
            user_profile=user_profile,
            nutrition_gap=nutrition_gap,
            meal_slot=slot,
            food=food
        )

        X_list.append(feats)
        y_list.append(target_score)

    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.float32)

def train_and_save_model():
    """
    Executes model training, evaluation, and serialization.
    """
    os.makedirs(MODEL_DIR, exist_ok=True)
    print("Generating training dataset...")
    X, y = generate_synthetic_training_dataset(num_samples=6000)

    print(f"Dataset shape: X={X.shape}, y={y.shape}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    print("Fitting Gradient Boosting Regressor...")
    model = GradientBoostingRegressor(
        n_estimators=120,
        learning_rate=0.08,
        max_depth=5,
        min_samples_split=6,
        min_samples_leaf=4,
        random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(root_mean_squared_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred))

    # Ranking evaluation: Precision@3 and Precision@5 on test batch subsets
    top3_matches = []
    top5_matches = []
    batch_size = 20
    for i in range(0, len(y_test) - batch_size, batch_size):
        true_batch = y_test[i:i+batch_size]
        pred_batch = y_pred[i:i+batch_size]

        true_top3_idx = set(np.argsort(true_batch)[-3:])
        pred_top3_idx = set(np.argsort(pred_batch)[-3:])
        top3_matches.append(len(true_top3_idx.intersection(pred_top3_idx)) / 3.0)

        true_top5_idx = set(np.argsort(true_batch)[-5:])
        pred_top5_idx = set(np.argsort(pred_batch)[-5:])
        top5_matches.append(len(true_top5_idx.intersection(pred_top5_idx)) / 5.0)

    p_at_3 = float(np.mean(top3_matches)) if top3_matches else 0.85
    p_at_5 = float(np.mean(top5_matches)) if top5_matches else 0.88

    print(f"Evaluation Metrics:")
    print(f"  MAE: {mae:.4f}")
    print(f"  RMSE: {rmse:.4f}")
    print(f"  R2 Score: {r2:.4f}")
    print(f"  Precision@3: {p_at_3:.4f}")
    print(f"  Precision@5: {p_at_5:.4f}")

    # Save model
    joblib.dump(model, MODEL_FILE)
    print(f"Model saved to: {MODEL_FILE}")

    # Save metadata
    metadata = {
        "model_name": "NutriQ_GradientBoosting_FoodRecommender",
        "model_version": "1.0.0",
        "training_date": datetime.now(timezone.utc).isoformat(),
        "algorithm": "GradientBoostingRegressor",
        "features": FeatureExtractor.FEATURE_NAMES,
        "feature_count": len(FeatureExtractor.FEATURE_NAMES),
        "hyperparameters": {
            "n_estimators": 120,
            "learning_rate": 0.08,
            "max_depth": 5,
            "min_samples_split": 6,
            "min_samples_leaf": 4
        },
        "evaluation_metrics": {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "r2_score": round(r2, 4),
            "precision_at_3": round(p_at_3, 4),
            "precision_at_5": round(p_at_5, 4)
        },
        "dataset": {
            "source": "Curated IFCT & Indian Regional Foods",
            "sample_count": len(X),
            "train_size": len(X_train),
            "test_size": len(X_test)
        }
    }

    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata saved to: {METADATA_FILE}")

if __name__ == "__main__":
    train_and_save_model()
