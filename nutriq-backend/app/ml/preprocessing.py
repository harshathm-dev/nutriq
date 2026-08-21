import re
from typing import Dict, Any, List
import numpy as np

class FeatureExtractor:
    """
    Feature engineering pipeline for NutriQ ML Food Recommendation.
    Transforms (User Profile, Nutrition Gap State, Meal Context, Food Item, User History)
    into a standardized feature vector.
    """

    FEATURE_NAMES = [
        "calorie_gap",
        "protein_gap",
        "carb_gap",
        "fat_gap",
        "fiber_gap",
        "food_calories",
        "food_protein",
        "food_carbs",
        "food_fat",
        "food_fiber",
        "calorie_ratio",
        "protein_ratio",
        "calorie_density",
        "protein_density",
        "fiber_density",
        "is_breakfast",
        "is_lunch",
        "is_snack",
        "is_dinner",
        "slot_compatibility",
        "is_weight_loss",
        "is_muscle_gain",
        "is_maintain",
        "is_weight_gain",
        "user_bmi",
        "user_history_frequency"
    ]

    @classmethod
    def compute_slot_compatibility(cls, food_name: str, food_category: str, slot: str) -> float:
        """
        Estimates cultural and physiological slot compatibility between 0.0 and 1.0.
        """
        name = (food_name or "").lower()
        cat = (food_category or "").lower()
        slot = (slot or "").lower()

        breakfast_terms = ["dosa", "idli", "upma", "poha", "pongal", "cheela", "chilla", "pancake", "porridge", "daliya", "oatmeal", "omelette", "omlet", "sandwich", "thepla", "bread", "toast"]
        lunch_terms = ["rice", "biryani", "biriyani", "pulao", "dal", "sambar", "sambhar", "kootu", "rajma", "chana", "curry", "chicken", "fish", "mutton", "avial", "poriyal", "bhaat", "roti", "chapati"]
        snack_terms = ["fruit", "apple", "papaya", "banana", "orange", "guava", "grape", "cooler", "sharbat", "almond", "walnut", "seeds", "coconut water", "smoothie", "milkshake", "yogurt", "curd", "dahi", "buttermilk", "lassi", "sundal", "makhana", "sprouts", "cutlet", "chaat", "bhel", "pakoda", "pakora", "samosa", "chikki", "paniyaram", "tea", "chai", "coffee", "biscuit", "peanuts", "corn"]
        dinner_terms = ["roti", "chapati", "phulka", "soup", "paneer tikka", "grilled", "khichdi", "rasam", "salad", "dal", "curry", "stew", "fish", "chicken breast", "tofu", "bhurji"]

        if slot in ["breakfast"]:
            if any(k in name for k in breakfast_terms) or cat in ["dosa", "idli", "breakfast"]:
                return 1.0
            if any(k in name for k in snack_terms):
                return 0.7
            if any(k in name for k in lunch_terms):
                return 0.4
            return 0.5

        elif slot in ["lunch"]:
            if any(k in name for k in lunch_terms) or cat in ["rice", "legumes", "main_course"]:
                return 1.0
            if any(k in name for k in dinner_terms):
                return 0.8
            if any(k in name for k in breakfast_terms):
                return 0.4
            return 0.5

        elif slot in ["evening_snack", "snack", "mid_morning"]:
            if any(k in name for k in snack_terms) or cat in ["snacks", "chutneys", "fruits", "beverages"]:
                return 1.0
            if any(k in name for k in breakfast_terms):
                return 0.5
            if any(k in name for k in lunch_terms):
                return 0.2
            return 0.4

        elif slot in ["dinner"]:
            if any(k in name for k in dinner_terms) or cat in ["main_course", "curries", "legumes"]:
                return 1.0
            if any(k in name for k in lunch_terms):
                return 0.8
            if any(k in name for k in snack_terms):
                return 0.5
            return 0.4

        return 0.6

    @classmethod
    def extract_features(
        cls,
        user_profile: Dict[str, Any],
        nutrition_gap: Dict[str, Any],
        meal_context: str,
        food_item: Dict[str, Any],
        user_history_freq: float = 0.0
    ) -> List[float]:
        """
        Extract a single feature vector representing the (User, NutritionGap, Context, Food) tuple.
        """
        # 1. Nutrition Gap
        cal_gap = float(nutrition_gap.get("calories_remaining", 500.0))
        pro_gap = float(nutrition_gap.get("protein_remaining", 30.0))
        carb_gap = float(nutrition_gap.get("carbs_remaining", 70.0))
        fat_gap = float(nutrition_gap.get("fat_remaining", 20.0))
        fib_gap = float(nutrition_gap.get("fiber_remaining", 10.0))

        # 2. Food Properties
        f_cal = float(food_item.get("calories", 100.0) or 100.0)
        f_pro = float(food_item.get("protein_g", 4.0) or 4.0)
        f_carb = float(food_item.get("carbs_g", 15.0) or 15.0)
        f_fat = float(food_item.get("fat_g", 3.0) or 3.0)
        f_fib = float(food_item.get("fiber_g", 1.0) or 1.0)
        serving_grams = float(food_item.get("serving_grams", 100.0) or 100.0)

        # 3. Calculated Ratios & Densities
        if cal_gap > 50:
            cal_ratio = min(3.0, f_cal / cal_gap)
        elif cal_gap > 0:
            cal_ratio = min(3.0, f_cal / 100.0)
        else:
            # Over budget: ratio measures penalty of additional calories
            cal_ratio = f_cal / 100.0

        pro_ratio = f_pro / max(5.0, pro_gap) if pro_gap > 0 else f_pro / 10.0
        cal_density = f_cal / max(1.0, serving_grams)
        pro_density = f_pro / max(0.1, f_cal / 100.0)
        fib_density = f_fib / max(0.1, f_cal / 100.0)

        # 4. Meal Slot Encoding
        slot_lower = (meal_context or "snack").lower()
        is_breakfast = 1.0 if "breakfast" in slot_lower else 0.0
        is_lunch = 1.0 if "lunch" in slot_lower else 0.0
        is_snack = 1.0 if any(s in slot_lower for s in ["snack", "mid_morning", "evening"]) else 0.0
        is_dinner = 1.0 if "dinner" in slot_lower else 0.0

        slot_compat = cls.compute_slot_compatibility(
            food_item.get("name", ""),
            food_item.get("category", ""),
            slot_lower
        )

        # 5. Goal Encoding
        goal = (user_profile.get("fitness_goal") or user_profile.get("goal") or "maintain").lower()
        is_weight_loss = 1.0 if "loss" in goal or "cut" in goal else 0.0
        is_muscle_gain = 1.0 if "muscle" in goal or "bulk" in goal else 0.0
        is_maintain = 1.0 if "maintain" in goal else 0.0
        is_weight_gain = 1.0 if "gain" in goal and not is_muscle_gain else 0.0

        # 6. User Profile Metrics
        height_cm = float(user_profile.get("height_cm", 170.0) or 170.0)
        weight_kg = float(user_profile.get("weight_kg", 65.0) or 65.0)
        height_m = max(1.0, height_cm / 100.0)
        user_bmi = weight_kg / (height_m * height_m)

        # 7. User History Frequency
        history_freq = float(max(0.0, min(1.0, user_history_freq)))

        return [
            cal_gap,
            pro_gap,
            carb_gap,
            fat_gap,
            fib_gap,
            f_cal,
            f_pro,
            f_carb,
            f_fat,
            f_fib,
            cal_ratio,
            pro_ratio,
            cal_density,
            pro_density,
            fib_density,
            is_breakfast,
            is_lunch,
            is_snack,
            is_dinner,
            slot_compat,
            is_weight_loss,
            is_muscle_gain,
            is_maintain,
            is_weight_gain,
            user_bmi,
            history_freq
        ]
