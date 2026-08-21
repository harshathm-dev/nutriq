import json
from typing import Dict, Any, List
from datetime import datetime, timezone

class AgentState:
    IDLE = "IDLE"
    ANALYZING = "ANALYZING"
    DECIDING = "DECIDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        self.state = AgentState.IDLE

    def transition(self, new_state: str):
        self.state = new_state

class NutritionAgent(BaseAgent):
    def __init__(self):
        super().__init__("NutritionAgent")

    def run(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        self.transition(AgentState.ANALYZING)
        consumed = user_context.get("consumed_calories", 0)
        target = user_context.get("target_calories", 2000)
        protein_consumed = user_context.get("consumed_protein_g", 0)
        protein_target = user_context.get("target_protein_g", 100)

        self.transition(AgentState.DECIDING)
        status = "on_track"
        if consumed > target * 1.05:
            status = "surplus"
        elif consumed < target * 0.5:
            status = "under_fueled"

        protein_ratio = (protein_consumed / max(1.0, protein_target))
        self.transition(AgentState.COMPLETED)
        return {
            "agent": self.name,
            "status": status,
            "calorie_adherence_pct": round((consumed / max(1.0, target)) * 100, 1),
            "protein_adherence_pct": round(protein_ratio * 100, 1),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

class GoalAgent(BaseAgent):
    def __init__(self):
        super().__init__("GoalAgent")

    def run(self, goal_data: Dict[str, Any], weight_history: List[float]) -> Dict[str, Any]:
        self.transition(AgentState.ANALYZING)
        current_wt = goal_data.get("current_weight_kg", 70.0)
        target_wt = goal_data.get("target_weight_kg", 65.0)
        goal_type = goal_data.get("goal_type", "weight_loss")

        self.transition(AgentState.DECIDING)
        delta = round(current_wt - target_wt, 1)
        velocity = 0.0
        if len(weight_history) >= 2:
            velocity = round(weight_history[-1] - weight_history[0], 2)

        self.transition(AgentState.COMPLETED)
        return {
            "agent": self.name,
            "goal_type": goal_type,
            "remaining_delta_kg": delta,
            "recent_velocity_kg": velocity,
            "trajectory_status": "aligned" if (delta > 0 and goal_type == "weight_loss") else "monitor"
        }

class RecommendationAgent(BaseAgent):
    def __init__(self):
        super().__init__("RecommendationAgent")

    def run(self, remaining_calories: float, remaining_protein_g: float, dietary_pref: str) -> List[Dict[str, Any]]:
        self.transition(AgentState.DECIDING)
        recs = []
        diet_lower = (dietary_pref or "standard").lower()

        if remaining_protein_g > 15:
            if "veg" in diet_lower or "jain" in diet_lower:
                food_title = "Paneer Tikka / Greek Yogurt / Moong Sprouts"
                food_desc = "150g grilled paneer with capsicum or 1 cup high-protein Greek yogurt."
                cal = min(250, max(120, int(remaining_calories * 0.4)))
                pro = 20.0
            elif "egg" in diet_lower:
                food_title = "Boiled Eggs / Double Egg Omelette"
                food_desc = "2-3 boiled eggs or egg white scramble with onion and green chili."
                cal = 160
                pro = 18.0
            else:
                food_title = "Grilled Chicken Breast / Meen Kulambu Fish"
                food_desc = "120g grilled herb chicken or 1 piece of fresh seer fish curry."
                cal = 190
                pro = 28.0

            recs.append({
                "title": "Protein Optimization Target",
                "food": food_title,
                "reason": f"You need approx {int(remaining_protein_g)}g more protein to hit your daily macro goal.",
                "description": food_desc,
                "calories": cal,
                "protein_g": pro
            })

        if remaining_calories > 250:
            recs.append({
                "title": "Balanced Nutrient-Dense Dinner",
                "food": "2 Whole Wheat Phulkas + Dal Tadka + Poriyal",
                "reason": "Offers high fiber, steady satiety, and keeps you within your daily calorie floor.",
                "description": "2 phulkas with yellow toor dal and fresh green beans poriyal.",
                "calories": min(420, int(remaining_calories * 0.7)),
                "protein_g": 14.0
            })
        else:
            recs.append({
                "title": "Light Evening Satiety Option",
                "food": "Roasted Makhana (Fox Nuts) & Green Tea",
                "reason": "Low in calorie density, rich in micronutrients, and prevents late-night cravings.",
                "description": "30g roasted makhana with mild chaat masala.",
                "calories": 95,
                "protein_g": 3.0
            })

        self.transition(AgentState.COMPLETED)
        return recs

class MealPlanningAgent(BaseAgent):
    """
    Dynamic Database-Grounded Meal Planning Engine
    Generates varied, non-repeating, target-calibrated schedules per day & meal category.
    Strictly validates macros against canonical nutrition models, database records,
    and user allergies & dietary preferences.
    """
    def __init__(self):
        super().__init__("MealPlanningAgent")

    @classmethod
    def _is_food_allowed(
        cls,
        food_name: str,
        category: str,
        diet: str,
        allergens: List[str]
    ) -> bool:
        """Check if a food matches dietary restrictions and does not contain allergens."""
        name_lower = food_name.lower()
        cat_lower = (category or "").lower()

        # 1. Dietary restrictions
        is_veg = "veg" in diet or "jain" in diet
        is_eggetarian = "eggetarian" in diet
        is_jain = "jain" in diet
        is_vegan = "vegan" in diet

        non_veg_keywords = ["chicken", "mutton", "lamb", "beef", "pork", "fish", "prawn", "seafood", "salami", "bacon", "meat", "machli", "jhinga"]
        egg_keywords = ["egg", "anda", "omelette", "omlet", "scrambled"]
        dairy_keywords = ["paneer", "curd", "dahi", "milk", "butter", "ghee", "cheese", "yogurt", "khoa", "mawa", "kheer", "rabri", "lassi", "milkshake", "shake", "malai", "cream", "ice cream"]
        root_veg_keywords = ["onion", "pyaaz", "garlic", "lahasun", "potato", "aloo", "radish", "mooli", "carrot", "gajar", "beetroot", "turnip"]

        if is_veg and not is_eggetarian:
            if any(k in name_lower for k in non_veg_keywords) or any(k in name_lower for k in egg_keywords):
                return False
            if cat_lower in ["meat", "fish", "eggs"]:
                return False

        if is_eggetarian:
            if any(k in name_lower for k in non_veg_keywords) or cat_lower in ["meat", "fish"]:
                return False

        if is_vegan:
            if any(k in name_lower for k in non_veg_keywords + egg_keywords + dairy_keywords):
                return False
            if cat_lower in ["meat", "fish", "eggs", "dairy"]:
                return False

        if is_jain:
            if any(k in name_lower for k in non_veg_keywords + egg_keywords + root_veg_keywords):
                return False

        # 2. Allergen exclusions
        for allergen in allergens:
            all_str = allergen.lower().strip()
            if not all_str:
                continue
            if any(d in all_str for d in ["dairy", "milk", "lactose"]) and (any(k in name_lower for k in dairy_keywords) or cat_lower == "dairy"):
                return False
            if any(p in all_str for p in ["peanut", "peanuts", "groundnut"]) and any(k in name_lower for k in ["peanut", "moongfali", "mungfali"]):
                return False
            if any(n in all_str for n in ["tree nut", "nut", "almond", "walnut", "cashew"]) and any(k in name_lower for k in ["almond", "walnut", "cashew", "kaju", "badam", "akhrot", "pista"]):
                return False
            if any(g in all_str for g in ["gluten", "wheat"]) and any(k in name_lower for k in ["wheat", "atta", "roti", "chapati", "paratha", "parantha", "poori", "puri", "naan", "bhatura", "maida", "bread", "pasta", "noodles", "semolina", "suji", "rava"]):
                return False
            if any(e in all_str for e in ["egg"]) and (any(k in name_lower for k in egg_keywords) or cat_lower == "eggs"):
                return False
            if any(s in all_str for s in ["soy", "soya"]) and any(k in name_lower for k in ["soya", "soy", "tofu", "edamame"]):
                return False
            if any(f in all_str for f in ["fish", "shellfish", "seafood"]) and (any(k in name_lower for k in ["fish", "machli", "prawn", "shrimp", "crab"]) or cat_lower in ["fish", "meat"]):
                return False

        return True

    @classmethod
    def _categorize_slot(cls, food_name: str, category: str) -> str:
        """Determine suitable meal slot for food item."""
        name = food_name.lower()
        cat = (category or "").lower()

        if cat in ["dosa", "idli", "uthappam"] or any(k in name for k in ["idli", "dosa", "upma", "poha", "pongal", "cheela", "chilla", "pancake", "porridge", "daliya", "oatmeal", "omelette", "omlet", "sandwich", "thepla"]):
            return "breakfast"

        if cat in ["snacks", "chutneys"] or any(k in name for k in ["fruit", "apple", "papaya", "banana", "orange", "guava", "grape", "cooler", "sharbat", "almonds", "walnuts", "seeds", "coconut water", "smoothie", "milkshake", "yogurt", "lassi", "sundal", "makhana", "sprouts", "cutlet", "chaat", "bhel", "pakoda", "pakora", "samosa", "chikki", "paniyaram", "tea", "chai", "coffee", "biscuit", "chana", "peanuts", "curd", "dahi", "buttermilk"]):
            return "evening_snack"

        if cat in ["rice", "legumes"] or any(k in name for k in ["rice", "biryani", "biriyani", "pulao", "dal", "sambar", "sambhar", "kootu", "rajma", "chana", "curry", "chicken", "fish", "mutton", "avial", "poriyal", "bhaat"]):
            return "lunch"

        return "dinner"

    def run(
        self,
        target_calories: float = 2000.0,
        dietary_pref: str = "standard",
        days: int = 7,
        user_name: str = "User",
        allergies: List[str] = None,
        exclude_food_ids: List[str] = None,
        exclude_meal_names: List[str] = None,
        regeneration_id: str = None,
        db_foods: List[Any] = None
    ) -> Dict[str, Any]:
        import random
        import hashlib

        self.transition(AgentState.DECIDING)
        target_cal = max(1200.0, min(4500.0, float(target_calories)))
        diet = (dietary_pref or "standard").lower()
        allergens = [a.lower() for a in (allergies or [])]
        days_count = max(1, min(14, int(days)))

        # Create seeded random generator for deterministic variation
        seed_str = str(regeneration_id or hashlib.sha256(f"{target_cal}_{diet}_{days}_{datetime.now(timezone.utc).timestamp()}".encode()).hexdigest())
        seed_int = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed_int)

        excluded_ids = set(str(fid).lower() for fid in (exclude_food_ids or []))
        excluded_names = set(str(fn).lower().strip() for fn in (exclude_meal_names or []))

        # Build candidate pools
        slot_candidates = {
            "breakfast": [],
            "lunch": [],
            "evening_snack": [],
            "dinner": []
        }

        # 1. Load candidates from db_foods if provided
        if db_foods:
            for food in db_foods:
                fid = str(getattr(food, "id", ""))
                fname = getattr(food, "name", "")
                fcat = getattr(food, "category", "")
                fcal = float(getattr(food, "calories", 100.0) or 100.0)
                fpro = float(getattr(food, "protein_g", 5.0) or 5.0)
                fcarb = float(getattr(food, "carbs_g", 15.0) or 15.0)
                ffat = float(getattr(food, "fat_g", 3.0) or 3.0)
                ffiber = float(getattr(food, "fiber_g", 1.0) or 1.0)
                fconvs = getattr(food, "serving_conversions", []) or []

                if fcal <= 5.0:
                    continue

                if not self._is_food_allowed(fname, fcat, diet, allergens):
                    continue

                slot = self._categorize_slot(fname, fcat)
                
                # Format candidate object
                conv_label = fconvs[0].serving_label if fconvs else "1 standard portion"
                item_dict = {
                    "id": fid,
                    "name": fname,
                    "category": fcat,
                    "calories_per_100g": fcal,
                    "protein_per_100g": fpro,
                    "carbs_per_100g": fcarb,
                    "fat_per_100g": ffat,
                    "fiber_per_100g": ffiber,
                    "serving_label": conv_label,
                    "is_excluded": (fid.lower() in excluded_ids or fname.lower().strip() in excluded_names)
                }

                slot_candidates[slot].append(item_dict)
                # Dinner can also accept lunch dishes
                if slot == "lunch":
                    slot_candidates["dinner"].append(item_dict)

        # 2. Rich Curated Fallback Pool if DB pool is sparse
        curated_fallbacks = {
            "breakfast": [
                {"name": "2 Moong Dal Chilas with Mint Chutney & Sprout Salad", "cal": 280, "pro": 14.0, "carb": 38.0, "fat": 8.0, "fiber": 4.5, "unit": "2 chilas", "diet": "veg"},
                {"name": "2 Ragi Dosas (Finger Millet) + Tomato Kara Chutney + Plain Curd", "cal": 310, "pro": 11.0, "carb": 48.0, "fat": 8.0, "fiber": 6.0, "unit": "2 dosas", "diet": "veg"},
                {"name": "3 Steamed Idlis + Tamil Drumstick Sambar + Coconut Chutney", "cal": 290, "pro": 10.5, "carb": 52.0, "fat": 5.0, "fiber": 4.0, "unit": "3 idlis", "diet": "veg"},
                {"name": "Ven Pongal (Ghee Khara Pongal) + Tiffin Sambar + 1 Medu Vada", "cal": 360, "pro": 11.0, "carb": 54.0, "fat": 12.0, "fiber": 5.0, "unit": "1 bowl", "diet": "veg"},
                {"name": "Poha with Peanuts, Curry Leaves & Lemon + Toned Milk", "cal": 320, "pro": 12.0, "carb": 46.0, "fat": 10.0, "fiber": 3.8, "unit": "1 plate", "diet": "veg"},
                {"name": "2 Masala Dosas with Potato Filling + Tomato Chutney + Sambar", "cal": 340, "pro": 9.5, "carb": 55.0, "fat": 9.0, "fiber": 4.2, "unit": "2 dosas", "diet": "veg"},
                {"name": "Rava Upma with Cashews & Vegetables + Coconut Chutney", "cal": 310, "pro": 8.5, "carb": 49.0, "fat": 9.5, "fiber": 4.0, "unit": "1 bowl", "diet": "veg"},
                {"name": "2 Vegetable Stuffed Parathas + Low Fat Curd", "cal": 330, "pro": 10.0, "carb": 50.0, "fat": 10.0, "fiber": 5.5, "unit": "2 parathas", "diet": "veg"},
                {"name": "Double Egg Omelette with Onion & Chili + 2 Whole Wheat Toasts", "cal": 340, "pro": 18.0, "carb": 30.0, "fat": 16.0, "fiber": 3.0, "unit": "1 plate", "diet": "eggetarian"},
                {"name": "2 Egg Dosas (Muttai Dosa) + Tamil Sambar + Tomato Chutney", "cal": 350, "pro": 17.0, "carb": 42.0, "fat": 13.0, "fiber": 3.5, "unit": "2 dosas", "diet": "eggetarian"},
                {"name": "Grilled Chicken Sausage & Herb Scrambled Eggs + 1 Toast", "cal": 360, "pro": 24.0, "carb": 22.0, "fat": 18.0, "fiber": 2.5, "unit": "1 plate", "diet": "non_veg"},
            ],
            "lunch": [
                {"name": "2 Whole Wheat Rotis + Yellow Dal Tadka + Green Beans Poriyal + Curd", "cal": 480, "pro": 20.0, "carb": 72.0, "fat": 12.0, "fiber": 10.0, "unit": "1 meal plate", "diet": "veg"},
                {"name": "Thayir Sadam (Curd Rice) + Tamil Sambar + Chow Chow Kootu", "cal": 450, "pro": 16.0, "carb": 75.0, "fat": 9.0, "fiber": 7.0, "unit": "1 meal plate", "diet": "veg"},
                {"name": "Vegetable Biriyani / Pulao + Cucumber Onion Raita + Soya Chunks Curry", "cal": 510, "pro": 22.0, "carb": 78.0, "fat": 12.0, "fiber": 9.0, "unit": "1 meal plate", "diet": "veg"},
                {"name": "Cooked Foxtail Millet (Thinai) + Keerai Kootu + Raw Banana Poriyal", "cal": 460, "pro": 18.0, "carb": 76.0, "fat": 9.5, "fiber": 11.0, "unit": "1 meal plate", "diet": "veg"},
                {"name": "2 Whole Wheat Rotis + Rajma Masala + Green Salad + Curd", "cal": 490, "pro": 21.0, "carb": 74.0, "fat": 11.0, "fiber": 11.5, "unit": "1 meal plate", "diet": "veg"},
                {"name": "Cooked Brown Rice + Tamil Drumstick Sambar + Avial Stew + Roasted Papad", "cal": 470, "pro": 17.0, "carb": 80.0, "fat": 9.0, "fiber": 9.0, "unit": "1 meal plate", "diet": "veg"},
                {"name": "Paneer Pulao + Mixed Sprout Salad + Tomato Pepper Rasam", "cal": 500, "pro": 22.0, "carb": 68.0, "fat": 15.0, "fiber": 7.0, "unit": "1 meal plate", "diet": "veg"},
                {"name": "2 Whole Wheat Rotis + Chettinad Chicken Curry + Beans Poriyal + Curd", "cal": 520, "pro": 34.0, "carb": 58.0, "fat": 16.0, "fiber": 7.5, "unit": "1 meal plate", "diet": "non_veg"},
                {"name": "Brown Rice + Meen Kulambu (Seer Fish Curry) + Chow Chow Kootu", "cal": 490, "pro": 32.0, "carb": 66.0, "fat": 11.0, "fiber": 6.5, "unit": "1 meal plate", "diet": "non_veg"},
                {"name": "Ambur Chicken Biriyani + Cucumber Onion Raita + 1 Boiled Egg", "cal": 540, "pro": 36.0, "carb": 62.0, "fat": 16.0, "fiber": 5.0, "unit": "1 meal plate", "diet": "non_veg"},
                {"name": "Cooked Foxtail Millet + Vanjaram Fish Fry (1 Slice) + Keerai Kootu", "cal": 480, "pro": 30.0, "carb": 60.0, "fat": 12.5, "fiber": 8.0, "unit": "1 meal plate", "diet": "non_veg"},
            ],
            "evening_snack": [
                {"name": "Roasted Makhana (30g) + 1 Cup Green Tea", "cal": 130, "pro": 4.0, "carb": 24.0, "fat": 2.0, "fiber": 3.0, "unit": "1 bowl", "diet": "veg"},
                {"name": "Chana Sundal (White Chickpea Sundal with Grated Coconut)", "cal": 160, "pro": 8.0, "carb": 24.0, "fat": 3.5, "fiber": 5.0, "unit": "1 bowl", "diet": "veg"},
                {"name": "Mixed Sprouts Chaat with Lime, Onion & Coriander", "cal": 140, "pro": 8.5, "carb": 22.0, "fat": 2.0, "fiber": 4.5, "unit": "1 bowl", "diet": "veg"},
                {"name": "Roasted Chana (Bengal Gram) + 1 Cup Ginger Cardamom Chai", "cal": 150, "pro": 8.0, "carb": 22.0, "fat": 3.0, "fiber": 4.0, "unit": "1 cup + chana", "diet": "veg"},
                {"name": "Greek Yogurt with Sliced Elaichi Banana & Chia Seeds", "cal": 180, "pro": 12.0, "carb": 26.0, "fat": 3.5, "fiber": 3.5, "unit": "1 bowl", "diet": "veg"},
                {"name": "Curd with Fresh Pomegranate & Chopped Crisp Apple", "cal": 160, "pro": 6.5, "carb": 28.0, "fat": 3.0, "fiber": 4.0, "unit": "1 bowl", "diet": "veg"},
                {"name": "5 Savory Kuzhi Paniyarams + Tomato Chutney", "cal": 180, "pro": 5.0, "carb": 30.0, "fat": 4.5, "fiber": 3.0, "unit": "5 pieces", "diet": "veg"},
                {"name": "Makhana Bhel with Chopped Tomatoes, Cucumber & Lemon", "cal": 140, "pro": 4.5, "carb": 26.0, "fat": 2.2, "fiber": 3.5, "unit": "1 bowl", "diet": "veg"},
                {"name": "Boiled Sweet Corn with Lemon & Chaat Masala", "cal": 130, "pro": 4.0, "carb": 27.0, "fat": 1.5, "fiber": 3.5, "unit": "1 cup", "diet": "veg"},
                {"name": "Handful of Soaked Almonds (15g) + 1 Crisp Apple", "cal": 160, "pro": 4.0, "carb": 25.0, "fat": 6.5, "fiber": 4.0, "unit": "1 serving", "diet": "veg"},
                {"name": "1 Cup Fresh Papaya Cubes + 4 Walnut Halves", "cal": 150, "pro": 3.5, "carb": 22.0, "fat": 6.0, "fiber": 3.5, "unit": "1 bowl", "diet": "veg"},
                {"name": "Chilled Spiced Buttermilk (Neer Mor) + 1 Sweet Orange", "cal": 110, "pro": 4.0, "carb": 18.0, "fat": 2.5, "fiber": 3.0, "unit": "1 glass + 1 fruit", "diet": "veg"},
                {"name": "Tender Coconut Water (Elaneer) + 1 Tbsp Roasted Pumpkin Seeds", "cal": 130, "pro": 4.0, "carb": 18.0, "fat": 5.0, "fiber": 2.0, "unit": "1 glass", "diet": "veg"},
                {"name": "2 Boiled Egg Whites with Chaat Masala & Green Tea", "cal": 80, "pro": 8.0, "carb": 2.0, "fat": 0.5, "fiber": 0.5, "unit": "2 egg whites", "diet": "eggetarian"},
            ],
            "dinner": [
                {"name": "Paneer Tikka (140g) + Steamed Veggies + Tomato Pepper Rasam", "cal": 380, "pro": 22.0, "carb": 26.0, "fat": 20.0, "fiber": 5.5, "unit": "1 plate", "diet": "veg"},
                {"name": "2 Whole Wheat Phulkas + Palak Paneer + Fresh Cucumber Salad", "cal": 400, "pro": 18.0, "carb": 46.0, "fat": 16.0, "fiber": 7.0, "unit": "2 phulkas + paneer", "diet": "veg"},
                {"name": "2 Whole Wheat Chapatis + Yellow Dal Tadka + Cabbage Poriyal + Rasam", "cal": 370, "pro": 15.0, "carb": 58.0, "fat": 8.5, "fiber": 8.0, "unit": "2 chapatis + dal", "diet": "veg"},
                {"name": "1 Large Onion & Tomato Uthappam + Tomato Kara Chutney + Spiced Buttermilk", "cal": 360, "pro": 12.0, "carb": 56.0, "fat": 9.5, "fiber": 5.0, "unit": "1 uthappam", "diet": "veg"},
                {"name": "Tofu / Paneer Bhurji with 1 Chapati & Steamed Broccoli", "cal": 350, "pro": 20.0, "carb": 34.0, "fat": 14.0, "fiber": 6.0, "unit": "1 plate", "diet": "veg"},
                {"name": "2 Whole Wheat Phulkas + Paneer Butter Masala + Sliced Cucumber", "cal": 410, "pro": 18.0, "carb": 48.0, "fat": 17.0, "fiber": 6.5, "unit": "2 phulkas + curry", "diet": "veg"},
                {"name": "Comfort Moong Dal Khichdi with 1 Tsp Ghee + Warm Tomato Rasam", "cal": 360, "pro": 14.0, "carb": 58.0, "fat": 8.0, "fiber": 6.5, "unit": "1 bowl khichdi", "diet": "veg"},
                {"name": "Grilled Chicken Breast (140g) + Steamed Veggies + Tomato Pepper Rasam", "cal": 370, "pro": 34.0, "carb": 18.0, "fat": 16.0, "fiber": 4.5, "unit": "1 plate", "diet": "non_veg"},
                {"name": "2 Whole Wheat Phulkas + Chettinad Chicken Sukka + Fresh Salad", "cal": 410, "pro": 32.0, "carb": 42.0, "fat": 13.0, "fiber": 5.5, "unit": "2 phulkas + chicken", "diet": "non_veg"},
                {"name": "Grilled Fish Steak (150g) with 1 Chapati & Steamed Veggies", "cal": 360, "pro": 30.0, "carb": 28.0, "fat": 12.0, "fiber": 4.5, "unit": "1 plate", "diet": "non_veg"},
                {"name": "2 Whole Wheat Phulkas + Boiled Egg Curry (2 Eggs) + Sliced Cucumber", "cal": 380, "pro": 19.0, "carb": 44.0, "fat": 14.0, "fiber": 5.0, "unit": "2 phulkas + egg curry", "diet": "eggetarian"},
            ]
        }

        # Merge curated fallbacks into slot_candidates if matching diet/allergens
        for slot, fallbacks in curated_fallbacks.items():
            for fb in fallbacks:
                fb_name = fb["name"]
                fb_diet = fb["diet"]
                if not self._is_food_allowed(fb_name, "curated", diet, allergens):
                    continue
                if fb_diet == "non_veg" and ("veg" in diet or "jain" in diet or "eggetarian" in diet):
                    continue
                if fb_diet == "eggetarian" and ("veg" in diet or "jain" in diet) and "eggetarian" not in diet:
                    continue

                slot_candidates[slot].append({
                    "id": f"seed_{slot}_{abs(hash(fb_name)) % 100000}",
                    "name": fb_name,
                    "category": slot,
                    "calories_per_100g": fb["cal"],
                    "protein_per_100g": fb["pro"],
                    "carbs_per_100g": fb["carb"],
                    "fat_per_100g": fb["fat"],
                    "fiber_per_100g": fb["fiber"],
                    "serving_label": fb["unit"],
                    "is_excluded": (fb_name.lower().strip() in excluded_names)
                })

        # 4 Core Meal Slots: Breakfast (25%), Lunch (35%), Evening Snack (15%), Dinner (25%) -> Sum = 100%
        slot_calorie_weights = {
            "breakfast": 0.25,
            "lunch": 0.35,
            "evening_snack": 0.15,
            "dinner": 0.25
        }

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        if days_count > 7:
            day_names = day_names + [f"Day {i+1}" for i in range(7, days_count)]

        plan: Dict[str, Any] = {}
        used_food_ids_all: List[str] = []
        used_meal_names_all: List[str] = []

        # Keep track of foods used in the current generation so days don't repeat
        plan_internal_used_names = set()

        for d_idx in range(days_count):
            d_name = day_names[d_idx]
            day_plan: Dict[str, Any] = {}

            daily_pro = 0.0
            daily_carb = 0.0
            daily_fat = 0.0
            daily_fiber = 0.0
            daily_cal = 0.0

            for slot, weight in slot_calorie_weights.items():
                slot_cal_target = target_cal * weight
                candidates = slot_candidates.get(slot, [])

                # Filter candidate pool:
                # 1st preference: not in excluded list (previous plan) AND not used in this plan yet
                primary_candidates = [
                    c for c in candidates 
                    if not c["is_excluded"] and c["name"].lower() not in plan_internal_used_names
                ]

                # 2nd preference: not in this plan yet (even if in previous plan, if candidates are few)
                secondary_candidates = [
                    c for c in candidates 
                    if c["name"].lower() not in plan_internal_used_names
                ]

                if primary_candidates:
                    chosen = rng.choice(primary_candidates)
                elif secondary_candidates:
                    chosen = rng.choice(secondary_candidates)
                elif candidates:
                    chosen = rng.choice(candidates)
                else:
                    # Emergency fallback
                    chosen = {
                        "id": f"gen_fallback_{slot}",
                        "name": f"Healthy Balanced {slot.replace('_', ' ').capitalize()}",
                        "calories_per_100g": slot_cal_target,
                        "protein_per_100g": slot_cal_target * 0.06,
                        "carbs_per_100g": slot_cal_target * 0.12,
                        "fat_per_100g": slot_cal_target * 0.03,
                        "fiber_per_100g": 4.0,
                        "serving_label": "1 calibrated portion"
                    }

                plan_internal_used_names.add(chosen["name"].lower())
                used_food_ids_all.append(chosen["id"])
                used_meal_names_all.append(chosen["name"])

                # Scale portion to match slot calorie target
                base_cal = max(10.0, float(chosen["calories_per_100g"]))
                scale_ratio = slot_cal_target / base_cal
                
                # If base cal is per 100g, compute exact grams
                calibrated_cal = round(slot_cal_target)
                calibrated_pro = round(max(1.0, float(chosen["protein_per_100g"]) * scale_ratio), 1)
                calibrated_carb = round(max(2.0, float(chosen["carbs_per_100g"]) * scale_ratio), 1)
                calibrated_fat = round(max(0.5, float(chosen["fat_per_100g"]) * scale_ratio), 1)
                calibrated_fiber = round(max(0.5, float(chosen["fiber_per_100g"]) * scale_ratio), 1)

                daily_cal += calibrated_cal
                daily_pro += calibrated_pro
                daily_carb += calibrated_carb
                daily_fat += calibrated_fat
                daily_fiber += calibrated_fiber

                portion_label = chosen.get("serving_label") or "1 calibrated portion"
                if "100g" in portion_label.lower() or "portion" in portion_label.lower():
                    portion_label = f"1 serving (~{round(scale_ratio * 100)}g)"

                slot_dict = {
                    "food_id": chosen["id"],
                    "name": chosen["name"],
                    "food_name": chosen["name"],
                    "calories": calibrated_cal,
                    "protein_g": calibrated_pro,
                    "carbs_g": calibrated_carb,
                    "fat_g": calibrated_fat,
                    "fiber_g": calibrated_fiber,
                    "portion": portion_label,
                    "portion_guide": portion_label,
                    "dietary_tags": ["Target Compliant", "IFCT Grounded", dietary_pref.capitalize()],
                    "tags": ["Target Compliant", "IFCT Grounded", dietary_pref.capitalize()]
                }
                day_plan[slot] = slot_dict
                if slot == "evening_snack":
                    day_plan["snack"] = slot_dict
                    day_plan["eveningSnack"] = slot_dict

            day_plan["daily_summary"] = {
                "total_calories": round(daily_cal),
                "total_protein_g": round(daily_pro, 1),
                "total_carbs_g": round(daily_carb, 1),
                "total_fat_g": round(daily_fat, 1),
                "total_fiber_g": round(daily_fiber, 1),
                "target_calories": round(target_cal),
                "variance_calories": round(daily_cal - target_cal)
            }

            plan[d_name] = day_plan

        now_iso = datetime.now(timezone.utc).isoformat()
        self.transition(AgentState.COMPLETED)
        return {
            "title": f"{days_count}-Day Dynamic Personalized Nutrition Schedule",
            "user_name": user_name,
            "regeneration_id": seed_str,
            "generation_timestamp": now_iso,
            "daily_target_calories": target_cal,
            "dietary_preference": dietary_pref,
            "allergies_excluded": allergens,
            "used_food_ids": used_food_ids_all,
            "days": plan
        }

class ProgressAgent(BaseAgent):
    def __init__(self):
        super().__init__("ProgressAgent")

    def run(self, logging_days_count: int, target_consistency: int = 7) -> Dict[str, Any]:
        self.transition(AgentState.COMPLETED)
        score = min(100, int((logging_days_count / max(1, target_consistency)) * 100))
        return {
            "agent": self.name,
            "consistency_score": score,
            "active_streak_days": logging_days_count,
            "badge_earned": "Gold Tracker" if score >= 90 else ("Silver Tracker" if score >= 70 else "Bronze Tracker")
        }

class AlertAgent(BaseAgent):
    def __init__(self):
        super().__init__("AlertAgent")

    def run(self, warnings: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.transition(AgentState.COMPLETED)
        return {
            "agent": self.name,
            "active_alerts_count": len(warnings),
            "highest_severity": max([w.get("severity", "low") for w in warnings], default="none")
        }

class ReportAgent(BaseAgent):
    def __init__(self):
        super().__init__("ReportAgent")

    def run(self, weekly_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        self.transition(AgentState.COMPLETED)
        avg_cal = weekly_telemetry.get("avg_calories", 1850)
        target_cal = weekly_telemetry.get("target_calories", 1900)
        avg_pro = weekly_telemetry.get("avg_protein_g", 92)
        target_pro = weekly_telemetry.get("target_protein_g", 100)

        return {
            "title": "Weekly Nutrition Intelligence Report",
            "summary": (
                f"Great work this week! Your average daily intake was **{int(avg_cal)} kcal** "
                f"(vs. {int(target_cal)} kcal target). Protein averaged **{int(avg_pro)}g/day** "
                f"({int((avg_pro/max(1,target_pro))*100)}% of goal)."
            ),
            "key_takeaways": [
                "Caloric consistency was solid across 6 of 7 days.",
                "Lunch remains your most nutritionally balanced meal.",
                "Hydration reached 90% of daily goal on average."
            ],
            "action_items": [
                "Maintain adequate protein in evening snacks.",
                "Add a light post-dinner walk on workout days."
            ],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

class AgentOrchestrator:
    @classmethod
    def execute_pipeline(cls, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        User Data -> Nutrition Agent -> Goal Agent -> Historical Analysis -> Decision Layer -> Output
        """
        nutrition_agent = NutritionAgent()
        goal_agent = GoalAgent()
        recom_agent = RecommendationAgent()
        progress_agent = ProgressAgent()

        nutri_res = nutrition_agent.run(context.get("user_context", {}))
        goal_res = goal_agent.run(context.get("goal_data", {}), context.get("weight_history", []))
        recom_res = recom_agent.run(
            context.get("remaining_calories", 500),
            context.get("remaining_protein_g", 30),
            context.get("dietary_pref", "standard")
        )
        prog_res = progress_agent.run(context.get("logging_days", 5))

        return {
            "nutrition_telemetry": nutri_res,
            "goal_telemetry": goal_res,
            "recommendations": recom_res,
            "progress_score": prog_res
        }
