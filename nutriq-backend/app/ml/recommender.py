import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
import joblib
import numpy as np

from app.ml.preprocessing import FeatureExtractor

logger = logging.getLogger("nutriq.ml")

MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
MODEL_FILE = os.path.join(MODEL_DIR, "food_recommender_v1.joblib")
METADATA_FILE = os.path.join(MODEL_DIR, "metadata.json")

class MLFoodRecommender:
    """
    Production Inference Engine for ML-based Personalized Food Recommendation & Ranking.
    Applies strict pre-ML safety filters, extracts contextual feature vectors,
    predicts suitability scores, validates nutritional constraints, and synthesizes reasons.
    """

    _model = None
    _metadata = None
    _loaded = False
    _disabled = False

    # Allergen keyword mappings for strict deterministic safety
    ALLERGEN_KEYWORDS = {
        "dairy": ["milk", "curd", "paneer", "ghee", "butter", "cheese", "yogurt", "buttermilk", "lassi", "whey", "dahi", "milkshake", "shake", "malai", "cream"],
        "lactose": ["milk", "curd", "paneer", "ghee", "butter", "cheese", "yogurt", "buttermilk", "lassi", "whey", "dahi", "milkshake", "shake", "malai", "cream"],
        "gluten": ["wheat", "roti", "chapati", "parotta", "paratha", "bread", "pasta", "maida", "semolina", "rava", "sooji", "poori", "naan", "noodles", "atta"],
        "wheat": ["wheat", "roti", "chapati", "parotta", "paratha", "bread", "pasta", "maida", "semolina", "rava", "sooji", "poori", "naan", "noodles", "atta"],
        "peanut": ["peanut", "peanuts", "groundnut", "kadala", "kadalai", "moongfali", "mungfali"],
        "peanuts": ["peanut", "peanuts", "groundnut", "kadala", "kadalai", "moongfali", "mungfali"],
        "tree nut": ["almond", "badam", "cashew", "kaju", "walnut", "akhrot", "pista", "pistachio"],
        "tree nuts": ["almond", "badam", "cashew", "kaju", "walnut", "akhrot", "pista", "pistachio"],
        "nut": ["peanut", "almond", "badam", "cashew", "kaju", "walnut", "akhrot", "pista", "pistachio"],
        "nuts": ["peanut", "almond", "badam", "cashew", "kaju", "walnut", "akhrot", "pista", "pistachio"],
        "egg": ["egg", "eggs", "omelet", "omelette", "boiled egg", "egg bhurji", "anda"],
        "eggs": ["egg", "eggs", "omelet", "omelette", "boiled egg", "egg bhurji", "anda"],
        "fish": ["fish", "meen", "salmon", "tuna", "pomfret", "sardine", "mackerel", "machli", "vanjaram"],
        "shellfish": ["prawn", "shrimp", "crab", "lobster", "jhinga"],
        "seafood": ["fish", "meen", "prawn", "shrimp", "crab", "lobster", "salmon", "tuna", "machli"],
        "soy": ["soy", "soya", "tofu", "edamame"],
        "soya": ["soy", "soya", "tofu", "edamame"]
    }

    NON_VEG_KEYWORDS = ["chicken", "mutton", "lamb", "beef", "pork", "fish", "prawn", "shrimp", "crab", "egg", "meat", "machli", "jhinga", "salami", "bacon"]
    NON_VEGAN_KEYWORDS = NON_VEG_KEYWORDS + ["milk", "curd", "paneer", "ghee", "butter", "cheese", "yogurt", "buttermilk", "lassi", "honey", "whey", "dahi", "milkshake", "cream"]

    @classmethod
    def load_model(cls) -> bool:
        """
        Loads serialized model and metadata into class memory.
        """
        if cls._disabled:
            return False

        if cls._loaded and cls._model is not None:
            return True

        if os.path.exists(MODEL_FILE):
            try:
                cls._model = joblib.load(MODEL_FILE)
                if os.path.exists(METADATA_FILE):
                    with open(METADATA_FILE, "r") as f:
                        cls._metadata = json.load(f)
                cls._loaded = True
                logger.info(f"Loaded ML Food Recommendation Model v{cls.get_model_version()}")
                return True
            except Exception as e:
                logger.error(f"Failed to load ML model: {e}")
                cls._model = None
                cls._loaded = False
                return False
        return False

    @classmethod
    def is_available(cls) -> bool:
        """Checks if ML model is ready for inference."""
        if cls._disabled:
            return False
        return cls.load_model()

    @classmethod
    def get_model_version(cls) -> str:
        if cls._metadata:
            return cls._metadata.get("model_version", "1.0.0")
        return "1.0.0"

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return cls._metadata or {}

    @classmethod
    def apply_safety_filters(
        cls,
        candidate_foods: List[Dict[str, Any]],
        dietary_pref: str,
        user_allergies: List[str],
        exclude_food_ids: Optional[List[str]] = None,
        exclude_food_names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        CRITICAL HARD SAFETY FILTER:
        Filters out any candidate food that violates user allergies, dietary restrictions,
        or explicit exclusions BEFORE ML ranking.
        """
        diet = (dietary_pref or "standard").lower()
        allergens = [a.lower().strip() for a in (user_allergies or []) if a]
        excl_ids = set(str(fid).lower() for fid in (exclude_food_ids or []))
        excl_names = set(str(fn).lower().strip() for fn in (exclude_food_names or []))

        is_veg = "veg" in diet or "jain" in diet
        is_eggetarian = "eggetarian" in diet
        is_vegan = "vegan" in diet

        safe_candidates = []

        for food in candidate_foods:
            fid = str(food.get("id", "")).lower()
            fname = (food.get("name") or food.get("food_name") or "").lower()
            fcat = (food.get("category") or "").lower()
            fcal = float(food.get("calories", 0.0) or 0.0)

            # 1. Reject invalid / empty records
            if fcal <= 5.0 or not fname:
                continue

            # 2. Reject explicit user exclusions
            if fid in excl_ids or fname.strip() in excl_names:
                continue

            # 3. Allergen check (Strict token + keyword boundary matching)
            has_allergen = False
            for user_allergy in allergens:
                for all_key, keywords in cls.ALLERGEN_KEYWORDS.items():
                    if all_key in user_allergy:
                        for word in keywords:
                            if re.search(r'\b' + re.escape(word) + r'\b', fname) or word in fname or word in fcat:
                                has_allergen = True
                                break
                    if has_allergen:
                        break
                if has_allergen:
                    break

            if has_allergen:
                continue

            # 4. Dietary Restriction check
            if is_vegan:
                if any(w in fname for w in cls.NON_VEGAN_KEYWORDS) or fcat in ["dairy", "meat", "fish", "eggs", "poultry"]:
                    continue
            elif is_veg and not is_eggetarian:
                if any(w in fname for w in cls.NON_VEG_KEYWORDS) or any(w in fname for w in ["egg", "anda", "omelet", "omelette"]) or fcat in ["meat", "fish", "eggs", "poultry", "non-veg", "seafood"]:
                    continue
            elif is_eggetarian:
                if any(w in fname for w in cls.NON_VEG_KEYWORDS) or fcat in ["meat", "fish", "poultry", "seafood"]:
                    continue

            safe_candidates.append(food)

        return safe_candidates

    @classmethod
    def rank_foods(
        cls,
        candidate_foods: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        nutrition_status: Dict[str, Any],
        meal_context: str,
        user_history: Optional[Dict[str, float]] = None,
        limit: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Ranks candidate foods using the trained ML model.
        Falls back to rule-based ranking if ML model is unavailable.
        """
        # 1. Apply Hard Safety Filter
        diet_pref = user_profile.get("dietary_preference", "standard")
        allergies = user_profile.get("allergies", [])
        safe_foods = cls.apply_safety_filters(
            candidate_foods=candidate_foods,
            dietary_pref=diet_pref,
            user_allergies=allergies
        )

        if not safe_foods:
            return []

        # 2. Extract Nutrition Gap
        cal_gap = float(nutrition_status.get("calories_remaining", 500.0))
        pro_gap = float(nutrition_status.get("macros", {}).get("protein", {}).get("remaining", 30.0))
        carb_gap = float(nutrition_status.get("macros", {}).get("carbs", {}).get("remaining", 70.0))
        fat_gap = float(nutrition_status.get("macros", {}).get("fat", {}).get("remaining", 20.0))
        fib_gap = float(nutrition_status.get("macros", {}).get("fiber", {}).get("remaining", 10.0))

        nutrition_gap = {
            "calories_remaining": cal_gap,
            "protein_remaining": pro_gap,
            "carbs_remaining": carb_gap,
            "fat_remaining": fat_gap,
            "fiber_remaining": fib_gap
        }

        user_history_map = user_history or {}

        # 3. Model Inference or Fallback
        use_ml = cls.is_available()
        scored_foods = []

        if use_ml:
            try:
                feature_matrix = []
                for food in safe_foods:
                    freq = user_history_map.get(str(food.get("id")), 0.0)
                    feats = FeatureExtractor.extract_features(
                        user_profile=user_profile,
                        nutrition_gap=nutrition_gap,
                        meal_context=meal_context,
                        food_item=food,
                        user_history_freq=freq
                    )
                    feature_matrix.append(feats)

                X = np.array(feature_matrix, dtype=np.float32)
                predicted_scores = cls._model.predict(X)

                for food, score in zip(safe_foods, predicted_scores):
                    calibrated_score = float(max(0.10, min(0.99, round(float(score), 2))))
                    scored_foods.append((food, calibrated_score, "ml_model"))

            except Exception as e:
                logger.warning(f"ML inference error: {e}. Falling back to deterministic scoring.")
                use_ml = False

        if not use_ml:
            # Deterministic Fallback Scoring
            for food in safe_foods:
                fallback_score = cls._compute_deterministic_score(
                    food=food,
                    nutrition_gap=nutrition_gap,
                    user_profile=user_profile,
                    meal_slot=meal_context
                )
                scored_foods.append((food, fallback_score, "rule_based_fallback"))

        # 4. Sort by Suitability Score (Descending)
        scored_foods.sort(key=lambda x: x[1], reverse=True)

        # 5. Nutrition Constraint Check & Human-Readable Reason Generation
        results = []
        status_level = nutrition_status.get("status_level", "on_track")
        goal = (user_profile.get("fitness_goal") or "maintain").lower()

        for food, score, source in scored_foods[:limit * 2]:
            # Post-ranking constraint validation
            f_cal = float(food.get("calories", 0.0))
            f_pro = float(food.get("protein_g", 0.0))
            f_fib = float(food.get("fiber_g", 0.0))

            # Severe calorie surplus check: do not place >300 kcal foods at rank 1 if user is over target
            if status_level in ["significantly_above", "target_exceeded"] and f_cal > 250.0 and len(results) == 0:
                continue

            reason = cls._generate_nutritional_reason(
                food=food,
                score=score,
                cal_remaining=cal_gap,
                pro_remaining=pro_gap,
                goal=goal,
                status_level=status_level,
                meal_slot=meal_context
            )

            tags = []
            if f_pro >= 10.0:
                tags.append("High Protein")
            if f_fib >= 4.0:
                tags.append("High Fiber")
            if f_cal <= 130.0:
                tags.append("Low Calorie")
            if "veg" in diet_pref and "non" not in diet_pref:
                tags.append("Vegetarian")

            serving_qty = float(food.get("serving_quantity", 1.0) or 1.0)
            serving_unit = food.get("serving_unit") or food.get("unit") or "serving"
            serving_grams = float(food.get("serving_grams") or food.get("grams") or 100.0)

            results.append({
                "food_id": str(food.get("id", "")),
                "food_name": food.get("name") or food.get("food_name"),
                "category": food.get("category", "General").capitalize(),
                "serving_quantity": serving_qty,
                "serving_unit": serving_unit,
                "grams": serving_grams,
                "calories": round(f_cal, 1),
                "protein_g": round(f_pro, 1),
                "carbs_g": round(float(food.get("carbs_g", 0.0)), 1),
                "fat_g": round(float(food.get("fat_g", 0.0)), 1),
                "fiber_g": round(f_fib, 1),
                "meal_type": meal_context.lower(),
                "suitability_score": score,
                "model_version": cls.get_model_version(),
                "recommendation_source": source,
                "reason": reason,
                "dietary_tags": tags
            })

            if len(results) >= limit:
                break

        return results

    @classmethod
    def _compute_deterministic_score(
        cls,
        food: Dict[str, Any],
        nutrition_gap: Dict[str, Any],
        user_profile: Dict[str, Any],
        meal_slot: str
    ) -> float:
        cal_gap = float(nutrition_gap.get("calories_remaining", 500.0))
        pro_gap = float(nutrition_gap.get("protein_remaining", 30.0))
        f_cal = float(food.get("calories", 150.0))
        f_pro = float(food.get("protein_g", 5.0))
        f_fib = float(food.get("fiber_g", 2.0))

        score = 0.50
        if cal_gap <= 0:
            score += 0.25 if f_cal <= 150 else -0.20
        else:
            if f_cal <= cal_gap:
                score += 0.20
            else:
                score -= 0.15

        if pro_gap > 25 and f_pro >= 8.0:
            score += 0.15
        if f_fib >= 3.5:
            score += 0.10

        slot_compat = FeatureExtractor.compute_slot_compatibility(
            food.get("name", ""),
            food.get("category", ""),
            meal_slot
        )
        score += (slot_compat - 0.5) * 0.3

        return float(max(0.10, min(0.98, round(score, 2))))

    @classmethod
    def _generate_nutritional_reason(
        cls,
        food: Dict[str, Any],
        score: float,
        cal_remaining: float,
        pro_remaining: float,
        goal: str,
        status_level: str,
        meal_slot: str
    ) -> str:
        """
        Synthesizes a precise, data-grounded nutritional explanation reason.
        """
        f_cal = round(float(food.get("calories", 0.0)))
        f_pro = round(float(food.get("protein_g", 0.0)), 1)
        f_fib = round(float(food.get("fiber_g", 0.0)), 1)
        slot_label = meal_slot.replace("_", " ").title()

        if status_level in ["significantly_above", "target_exceeded"]:
            return f"Light, nutrient-dense choice ({f_cal} kcal, {f_fib}g fiber) suitable when near or above your daily calorie target."

        if pro_remaining >= 25.0 or "muscle" in goal:
            if f_pro >= 10.0:
                return f"High protein ({f_pro}g) and fits your remaining calorie budget ({int(cal_remaining)} kcal) to support lean muscle."
            return f"Provides {f_pro}g protein with balanced energy ({f_cal} kcal) for your {slot_label}."

        if "weight_loss" in goal:
            if f_fib >= 3.0:
                return f"Fiber-rich option ({f_fib}g fiber, {f_cal} kcal) that supports satiety within your weight-loss calorie target."
            return f"Fits your remaining budget ({int(cal_remaining)} kcal) with balanced nutrients for {slot_label}."

        if "weight_gain" in goal:
            return f"Nutrient-dense fuel ({f_cal} kcal, {f_pro}g protein) supporting your weight-gain progression."

        return f"Nutritionally balanced ({f_cal} kcal, {f_pro}g protein) tailored for your {slot_label}."
