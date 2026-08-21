import re
import random
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.models.food import Food, ServingConversion
from app.models.family import Allergy
from app.models.profile import UserProfile
from app.models.meal import Meal, MealItem
from app.services.food_service import CURATED_FOOD_SEEDS
from app.ml.recommender import MLFoodRecommender

class FoodRecommendationService:
    """
    Personalized Food Recommendation Engine powered by trained Machine Learning (GradientBoosting)
    and robust deterministic safety guards.
    Generates tailored, portion-specific food recommendations strictly from the active NutriQ database.
    Zero hallucinated foods, strict allergen safety, dietary restriction enforcement, and meal-slot context.
    """

    @classmethod
    async def get_recommendations(
        cls,
        session: AsyncSession,
        user_id: str,
        nutrition_status: Dict[str, Any],
        meal_type: Optional[str] = None,
        limit: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Generates personalized food recommendations using ML ranking based on live user nutrition status,
        remaining calories, macros, allergies, and diet.
        """
        # 1. Fetch User Profile and Allergies
        prof_stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        prof_res = await session.execute(prof_stmt)
        profile = prof_res.scalar_one_or_none()

        allergy_stmt = select(Allergy).where(Allergy.user_id == user_id)
        allergy_res = await session.execute(allergy_stmt)
        allergies = list(allergy_res.scalars().all())

        diet_pref = (profile.dietary_preference if profile else "standard").lower()
        allergens_list = [a.allergen_type.lower() for a in allergies]
        fitness_goal = (profile.fitness_goal if profile else "maintain").lower()

        # 2. Fetch User Meal History (Last 30 Days) for Behavioral Frequency Features
        history_map: Dict[str, float] = {}
        try:
            meal_stmt = (
                select(MealItem.food_name)
                .join(Meal, MealItem.meal_id == Meal.id)
                .where(Meal.user_id == user_id)
            )
            meal_res = await session.execute(meal_stmt)
            logged_names = [r[0].lower().strip() for r in meal_res.all() if r[0]]
            if logged_names:
                total_logged = len(logged_names)
                for name in logged_names:
                    history_map[name] = history_map.get(name, 0.0) + (1.0 / total_logged)
        except Exception as e:
            logger.warning(f"Error fetching meal history for user {user_id}: {e}")

        # 3. Determine Slot / Meal Type if not provided
        if not meal_type:
            now_hour = datetime.now(timezone.utc).hour + 5.5  # Approximate IST
            if now_hour < 11:
                target_slot = "breakfast"
            elif now_hour < 16:
                target_slot = "lunch"
            elif now_hour < 19:
                target_slot = "snack"
            else:
                target_slot = "dinner"
        else:
            target_slot = meal_type.lower()

        # 4. Query Food Database
        food_stmt = select(Food).options(selectinload(Food.serving_conversions))
        food_res = await session.execute(food_stmt)
        all_db_foods = list(food_res.scalars().all())

        if not all_db_foods:
            candidate_pool = cls._get_seed_candidates()
        else:
            candidate_pool = []
            for f in all_db_foods:
                conversions = list(f.serving_conversions) if f.serving_conversions else []
                first_conv = conversions[0] if conversions else None
                candidate_pool.append({
                    "id": str(f.id),
                    "name": f.name,
                    "food_name": f.name,
                    "category": f.category,
                    "serving_size": f.serving_size,
                    "unit": f.unit,
                    "calories": float(f.calories or 0.0),
                    "protein_g": float(f.protein_g or 0.0),
                    "carbs_g": float(f.carbs_g or 0.0),
                    "fat_g": float(f.fat_g or 0.0),
                    "fiber_g": float(f.fiber_g or 0.0),
                    "serving_label": first_conv.serving_label if first_conv else "1 serving",
                    "serving_grams": first_conv.grams if first_conv else 100.0
                })

        # 5. Build User Profile Dict for ML Inference
        user_profile_dict = {
            "fitness_goal": fitness_goal,
            "dietary_preference": diet_pref,
            "allergies": allergens_list,
            "age": profile.age if profile else 30,
            "gender": profile.gender if profile else "male",
            "height_cm": profile.height_cm if profile else 170.0,
            "weight_kg": profile.weight_kg if profile else 70.0,
            "activity_level": profile.activity_level if profile else "moderately_active"
        }

        # 6. Rank Foods using ML Pipeline with Strict Pre-ML Safety Filter
        ranked_results = MLFoodRecommender.rank_foods(
            candidate_foods=candidate_pool,
            user_profile=user_profile_dict,
            nutrition_status=nutrition_status,
            meal_context=target_slot,
            user_history=history_map,
            limit=limit
        )

        if ranked_results:
            return ranked_results

        # 7. Fallback to Safe Seed Selection if ML pool is empty
        return cls._get_fallback_recommendations(
            candidate_pool=candidate_pool,
            user_profile=user_profile_dict,
            nutrition_status=nutrition_status,
            target_slot=target_slot,
            limit=limit
        )

    @classmethod
    def _get_fallback_recommendations(
        cls,
        candidate_pool: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        nutrition_status: Dict[str, Any],
        target_slot: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        safe_foods = MLFoodRecommender.apply_safety_filters(
            candidate_foods=candidate_pool,
            dietary_pref=user_profile.get("dietary_preference", "standard"),
            user_allergies=user_profile.get("allergies", [])
        )
        results = []
        for f in safe_foods[:limit]:
            results.append({
                "food_id": str(f.get("id", "")),
                "food_name": f.get("name"),
                "category": f.get("category", "General").capitalize(),
                "serving_quantity": 1.0,
                "serving_unit": f.get("serving_label", "serving"),
                "grams": float(f.get("serving_grams", 100.0)),
                "calories": float(f.get("calories", 100.0)),
                "protein_g": float(f.get("protein_g", 5.0)),
                "carbs_g": float(f.get("carbs_g", 15.0)),
                "fat_g": float(f.get("fat_g", 3.0)),
                "fiber_g": float(f.get("fiber_g", 2.0)),
                "meal_type": target_slot,
                "suitability_score": 0.75,
                "model_version": "fallback_v1",
                "recommendation_source": "rule_based_fallback",
                "reason": f"Wholesome choice ({f.get('calories', 100)} kcal) matching your dietary preferences.",
                "dietary_tags": ["Safe", "Catalog Grounded"]
            })
        return results

    @classmethod
    def _format_recommendation(cls, food: Dict[str, Any], slot: str, reason: str) -> Dict[str, Any]:
        serving_label = food.get("serving_label", "1 serving")
        serving_grams = float(food.get("serving_grams", 100.0))

        # Parse quantity and unit from serving label (e.g. "2 pieces", "1 cup", "150 g")
        match = re.match(r"^([\d\.]+)\s*(.*)$", serving_label)
        if match:
            qty = float(match.group(1))
            unit = match.group(2).strip() or "serving"
        else:
            qty = 1.0
            unit = serving_label

        tags = []
        if food.get("protein_g", 0) >= 10:
            tags.append("High Protein")
        if food.get("fiber_g", 0) >= 4:
            tags.append("High Fiber")
        if food.get("calories", 0) <= 120:
            tags.append("Low Calorie")

        return {
            "food_id": str(food.get("id", "food_" + food["name"][:5])),
            "food_name": food["name"],
            "category": food.get("category", "General"),
            "serving_quantity": qty,
            "serving_unit": unit,
            "grams": serving_grams,
            "calories": round(food.get("calories", 0.0), 1),
            "protein_g": round(food.get("protein_g", 0.0), 1),
            "carbs_g": round(food.get("carbs_g", 0.0), 1),
            "fat_g": round(food.get("fat_g", 0.0), 1),
            "fiber_g": round(food.get("fiber_g", 0.0), 1),
            "meal_type": slot,
            "reason": reason,
            "dietary_tags": tags
        }

    @classmethod
    async def get_smart_recommendations(
        cls,
        session: AsyncSession,
        user_id: str,
        target_date_str: Optional[str] = None,
        meal_type: Optional[str] = None,
        limit: int = 4
    ) -> Dict[str, Any]:
        """
        Unified smart recommendation pipeline that:
        1. Analyzes user profile, goals, and today's actual intake
        2. Calculates remaining daily nutrition needs & gaps
        3. Runs ML inference with strict safety and calorie limits
        4. Synthesizes human-readable reasons and gap analysis
        """
        from app.services.daily_summary_service import DailySummaryService
        from app.services.nutrition_warning_service import NutritionWarningService

        # 1. Fetch Daily Summary for Date
        daily_data = await DailySummaryService.get_daily_summary(
            session=session,
            user_id=user_id,
            target_date_str=target_date_str
        )

        cal_target = float(daily_data.get("calories", {}).get("target", 2000.0))
        cal_consumed = float(daily_data.get("calories", {}).get("consumed", 0.0))
        rem_cal = max(0.0, round(cal_target - cal_consumed, 1))

        pro_target = float(daily_data.get("macros", {}).get("protein", {}).get("target", 100.0))
        pro_consumed = float(daily_data.get("macros", {}).get("protein", {}).get("consumed", 0.0))
        rem_pro = max(0.0, round(pro_target - pro_consumed, 1))

        carb_target = float(daily_data.get("macros", {}).get("carbohydrates", {}).get("target", 250.0))
        carb_consumed = float(daily_data.get("macros", {}).get("carbohydrates", {}).get("consumed", 0.0))
        rem_carb = max(0.0, round(carb_target - carb_consumed, 1))

        fat_target = float(daily_data.get("macros", {}).get("fat", {}).get("target", 60.0))
        fat_consumed = float(daily_data.get("macros", {}).get("fat", {}).get("consumed", 0.0))
        rem_fat = max(0.0, round(fat_target - fat_consumed, 1))

        fib_target = float(daily_data.get("macros", {}).get("fiber", {}).get("target", 28.0))
        fib_consumed = float(daily_data.get("macros", {}).get("fiber", {}).get("consumed", 0.0))
        rem_fib = max(0.0, round(fib_target - fib_consumed, 1))

        water_target_ml = float(daily_data.get("hydration", {}).get("target_ml", 2500.0))
        water_consumed_ml = float(daily_data.get("hydration", {}).get("consumed_ml", 0.0))
        rem_water_l = max(0.0, round((water_target_ml - water_consumed_ml) / 1000.0, 1))

        is_empty_day = not bool(daily_data.get("has_data", False))
        is_future = bool(daily_data.get("is_future", False))
        goal = daily_data.get("goal", "weight_loss")
        goal_display = daily_data.get("goal_display", "Weight Loss")

        # 2. Determine Gaps
        protein_gap = "HIGH" if rem_pro > pro_target * 0.45 else ("MODERATE" if rem_pro > 15.0 else ("LOW" if rem_pro > 0 else "MET"))
        calorie_gap = "HIGH" if rem_cal > cal_target * 0.45 else ("MODERATE" if rem_cal > 200.0 else ("LOW" if rem_cal > 0 else "MET"))
        fiber_gap = "HIGH" if rem_fib > fib_target * 0.4 else ("MODERATE" if rem_fib > 5.0 else "MET")
        fat_gap = "MODERATE" if rem_fat > 10.0 else "MET"
        hydration_gap = "NEAR TARGET" if rem_water_l <= 0.5 else ("MODERATE" if rem_water_l <= 1.5 else "HIGH")

        # Determine target meal slot
        if not meal_type:
            meals_dict = daily_data.get("meals", {})
            if not meals_dict.get("breakfast", {}).get("logged"):
                target_slot = "breakfast"
            elif not meals_dict.get("lunch", {}).get("logged"):
                target_slot = "lunch"
            elif not meals_dict.get("snack", {}).get("logged"):
                target_slot = "snack"
            elif not meals_dict.get("dinner", {}).get("logged"):
                target_slot = "dinner"
            else:
                target_slot = "snack"
        else:
            target_slot = meal_type.lower()

        # 3. Nutrition Status Object for ML Engine
        nutrition_status_obj = {
            "calories_remaining": rem_cal,
            "calories_consumed": cal_consumed,
            "daily_calorie_target": cal_target,
            "status_level": daily_data.get("status_level", "on_track"),
            "macros": {
                "protein": {"remaining": rem_pro, "target": pro_target, "consumed": pro_consumed},
                "carbs": {"remaining": rem_carb, "target": carb_target, "consumed": carb_consumed, "is_exceeded": carb_consumed >= carb_target},
                "fat": {"remaining": rem_fat, "target": fat_target, "consumed": fat_consumed},
                "fiber": {"remaining": rem_fib, "target": fib_target, "consumed": fib_consumed}
            }
        }

        # 4. Run Recommendation Generation
        recommendations = await cls.get_recommendations(
            session=session,
            user_id=user_id,
            nutrition_status=nutrition_status_obj,
            meal_type=target_slot,
            limit=limit
        )

        # 5. Build Intelligent Warnings
        warnings = []
        if cal_consumed >= cal_target:
            warnings.append({
                "type": "calories_exceeded",
                "title": "Calorie Target Reached",
                "message": "You have reached your daily calorie target. Consider lower-calorie, nutrient-dense options for your next meal."
            })
        elif not is_empty_day and not is_future and cal_consumed < (cal_target * 0.70):
            warnings.append({
                "type": "below_target",
                "title": "Calorie Intake Below Target",
                "message": "Your calorie intake is currently below your daily target. Consider a balanced meal to support your goal and energy needs."
            })

        if carb_consumed >= carb_target:
            warnings.append({
                "type": "carbs_exceeded",
                "title": "Carbohydrates Reached Target",
                "message": "Your carbohydrate intake has reached today's target. Prioritize protein, fiber and nutrient-dense foods for your next meal."
            })

        if not is_empty_day and not is_future and rem_pro > (pro_target * 0.45):
            warnings.append({
                "type": "low_protein",
                "title": "Protein Intake Low",
                "message": "Your protein intake is low today. Consider adding a protein-rich food to help meet your daily target."
            })

        # 6. Build Response Object
        message = None
        if is_future:
            message = "Future date selected. Suggestions are tailored for your overall wellness goal."
        elif is_empty_day:
            message = f"Start logging today's meals to get personalized nutrition recommendations tailored to your {goal_display} goal."
        elif carb_consumed >= carb_target:
            message = "Carbohydrate target reached. High-protein and fiber-rich options prioritized."
        elif protein_gap == "HIGH":
            message = "High-protein choices prioritized to help close today's protein deficit within your calorie budget."
        elif calorie_gap == "LOW":
            message = "Light, nutrient-dense suggestions matching your remaining calorie budget."
        else:
            message = f"Personalized suggestions based on today's intake and your {goal_display} goal."

        return {
            "recommendations": recommendations,
            "remaining_needs": {
                "calories": rem_cal,
                "protein_g": rem_pro,
                "carbs_g": rem_carb,
                "fat_g": rem_fat,
                "fiber_g": rem_fib,
                "water_l": rem_water_l
            },
            "gaps": {
                "protein": protein_gap,
                "calories": calorie_gap,
                "fiber": fiber_gap,
                "fat": fat_gap,
                "hydration": hydration_gap
            },
            "goal": goal,
            "goal_display": goal_display,
            "target_meal_type": target_slot,
            "is_empty_day": is_empty_day,
            "is_future": is_future,
            "message": message,
            "warnings": warnings
        }

    @classmethod
    def _get_seed_candidates(cls) -> List[Dict[str, Any]]:
        pool = []
        for seed in CURATED_FOOD_SEEDS:
            conversions = seed.get("conversions", [])
            first_conv = conversions[0] if conversions else None
            pool.append({
                "id": "seed_" + seed["name"][:8],
                "name": seed["name"],
                "category": seed["category"],
                "serving_size": 100.0,
                "unit": "g",
                "calories": float(seed["calories"]),
                "protein_g": float(seed["protein_g"]),
                "carbs_g": float(seed["carbs_g"]),
                "fat_g": float(seed["fat_g"]),
                "fiber_g": float(seed.get("fiber_g", 0.0)),
                "serving_label": first_conv["label"] if first_conv else "1 serving",
                "serving_grams": first_conv["grams"] if first_conv else 100.0
            })
        return pool
