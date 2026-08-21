from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, date, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.meal import Meal, MealItem
from app.models.tracking import Water, Exercise, WeightHistory
from app.models.profile import UserProfile
from app.models.goal import Goal
from app.services.nutrition_engine import NutritionEngine
from app.services.meal_service import MealService


class DailySummaryService:
    @classmethod
    async def get_daily_summary(
        cls,
        session: AsyncSession,
        user_id: str,
        target_date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves the exact, un-fabricated daily nutrition summary for the authenticated user on a specific date.
        All numbers are grounded strictly in the user's recorded journal and targets.
        """
        tz = ZoneInfo("Asia/Kolkata")
        today_date = datetime.now(tz).date()

        if target_date_str:
            try:
                parsed_date = date.fromisoformat(target_date_str.split("T")[0])
            except Exception:
                parsed_date = today_date
        else:
            parsed_date = today_date

        is_today = (parsed_date == today_date)
        is_future = (parsed_date > today_date)

        start_of_day, end_of_day = MealService.get_date_bounds_utc(parsed_date, "Asia/Kolkata")

        # 1. Fetch User Profile and Active Goal for Canonical Targets
        prof_stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        prof_res = await session.execute(prof_stmt)
        profile = prof_res.scalar_one_or_none()

        goal_stmt = select(Goal).where(Goal.user_id == user_id, Goal.active == True)
        goal_res = await session.execute(goal_stmt)
        goal = goal_res.scalar_one_or_none()

        if profile and goal:
            calculated_targets = NutritionEngine.calculate_targets(
                weight_kg=profile.weight_kg,
                height_cm=profile.height_cm,
                age=profile.age,
                gender=profile.gender,
                activity_level=profile.activity_level,
                fitness_goal=goal.goal_type,
                desired_rate=goal.desired_rate,
                dietary_preference=profile.dietary_preference
            )
            fitness_goal = goal.goal_type
        elif profile:
            calculated_targets = NutritionEngine.calculate_targets(
                weight_kg=profile.weight_kg,
                height_cm=profile.height_cm,
                age=profile.age,
                gender=profile.gender,
                activity_level=profile.activity_level,
                fitness_goal=profile.fitness_goal,
                desired_rate=0.5,
                dietary_preference=profile.dietary_preference
            )
            fitness_goal = profile.fitness_goal
        else:
            calculated_targets = {
                "target_calories": 2000.0,
                "protein_g": 100.0,
                "carbs_g": 250.0,
                "fat_g": 60.0,
                "fiber_g": 28.0,
                "water_ml": 2500.0,
                "bmr": 1600.0,
                "tdee": 2200.0
            }
            fitness_goal = "weight_loss"

        cal_target = round(float(calculated_targets.get("target_calories", 2000.0)), 1)
        pro_target = round(float(calculated_targets.get("protein_g", 100.0)), 1)
        carb_target = round(float(calculated_targets.get("carbs_g", 250.0)), 1)
        fat_target = round(float(calculated_targets.get("fat_g", 60.0)), 1)
        fib_target = round(float(calculated_targets.get("fiber_g", 28.0)), 1)
        water_target = round(float(calculated_targets.get("water_ml", 2500.0)), 1)

        goal_display_map = {
            "weight_loss": "Weight Loss",
            "fat_loss": "Fat Loss",
            "maintain": "Weight Maintenance",
            "maintenance": "Weight Maintenance",
            "weight_gain": "Weight Gain",
            "muscle_building": "Muscle Building"
        }
        goal_display = goal_display_map.get(fitness_goal.lower(), "Weight Loss")

        # Future date guard — NEVER invent future data
        if is_future:
            display_date_str = parsed_date.strftime("%B %d, %Y")
            return {
                "date": parsed_date.isoformat(),
                "display_date": display_date_str,
                "is_today": False,
                "is_future": True,
                "has_data": False,
                "calories": {
                    "target": cal_target,
                    "consumed": 0.0,
                    "remaining": cal_target,
                    "burned": 0.0,
                    "net": 0.0,
                    "is_over": False,
                    "over_amount": 0.0
                },
                "macros": {
                    "protein": {"target": pro_target, "consumed": 0.0, "percentage": 0.0},
                    "carbohydrates": {"target": carb_target, "consumed": 0.0, "percentage": 0.0},
                    "fat": {"target": fat_target, "consumed": 0.0, "percentage": 0.0},
                    "fiber": {"target": fib_target, "consumed": 0.0, "percentage": 0.0}
                },
                "hydration": {
                    "target_ml": water_target,
                    "consumed_ml": 0.0,
                    "remaining_ml": water_target,
                    "percentage": 0.0,
                    "is_zero": True
                },
                "meals": {
                    "breakfast": {"logged": False, "status_label": "Not logged", "meal_count": 0, "total_calories": 0.0, "total_protein_g": 0.0, "total_carbs_g": 0.0, "total_fat_g": 0.0, "items": []},
                    "lunch": {"logged": False, "status_label": "Not logged", "meal_count": 0, "total_calories": 0.0, "total_protein_g": 0.0, "total_carbs_g": 0.0, "total_fat_g": 0.0, "items": []},
                    "snack": {"logged": False, "status_label": "Not logged", "meal_count": 0, "total_calories": 0.0, "total_protein_g": 0.0, "total_carbs_g": 0.0, "total_fat_g": 0.0, "items": []},
                    "dinner": {"logged": False, "status_label": "Not logged", "meal_count": 0, "total_calories": 0.0, "total_protein_g": 0.0, "total_carbs_g": 0.0, "total_fat_g": 0.0, "items": []},
                    "logged_count": 0,
                    "total_slots": 4
                },
                "exercise": {
                    "logged": False,
                    "duration_minutes": 0,
                    "calories_burned": 0.0,
                    "activities": [],
                    "items": [],
                    "message": "No exercise logged today."
                },
                "goal": fitness_goal,
                "goal_display": goal_display,
                "goal_status": "No nutrition data available yet.",
                "status_level": "no_meals",
                "status_badge": "No Meals Logged Yet",
                "calorie_status": NutritionEngine.calculate_calorie_status(cal_target, 0.0, 0.0, fitness_goal, has_meals=False),
                "daily_insight": "Future date selected. Log meals on that day to see your actual nutrition breakdown.",
                "calorie_warning": None,
                "progress_score": None,
                "progress_score_explanation": None,
                "empty_state_message": "No nutrition data available yet."
            }

        # 2. Fetch Meals for the Date
        meal_stmt = select(Meal).where(
            Meal.user_id == user_id,
            Meal.occurred_at >= start_of_day,
            Meal.occurred_at < end_of_day
        ).options(selectinload(Meal.items))
        meal_res = await session.execute(meal_stmt)
        meals = list(meal_res.scalars().all())

        # Categorize by slot
        slots = {
            "breakfast": {"logged": False, "items": [], "calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0},
            "lunch": {"logged": False, "items": [], "calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0},
            "snack": {"logged": False, "items": [], "calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0},
            "dinner": {"logged": False, "items": [], "calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0}
        }

        total_consumed_cal = 0.0
        total_consumed_pro = 0.0
        total_consumed_carb = 0.0
        total_consumed_fat = 0.0
        total_consumed_fib = 0.0

        for m in meals:
            m_type = (m.meal_type or "snack").lower()
            if "breakfast" in m_type or "morning" in m_type:
                slot_key = "breakfast"
            elif "lunch" in m_type or "afternoon" in m_type:
                slot_key = "lunch"
            elif "dinner" in m_type or "night" in m_type or "supper" in m_type:
                slot_key = "dinner"
            else:
                slot_key = "snack"

            slots[slot_key]["logged"] = True

            for item in m.items:
                cal = float(item.calories or 0)
                pro = float(item.protein_g or 0)
                carb = float(item.carbs_g or 0)
                fat = float(item.fat_g or 0)
                fib = float(item.fiber_g or 0)

                total_consumed_cal += cal
                total_consumed_pro += pro
                total_consumed_carb += carb
                total_consumed_fat += fat
                total_consumed_fib += fib

                slots[slot_key]["calories"] += cal
                slots[slot_key]["protein_g"] += pro
                slots[slot_key]["carbs_g"] += carb
                slots[slot_key]["fat_g"] += fat
                slots[slot_key]["fiber_g"] += fib

                slots[slot_key]["items"].append({
                    "food_name": item.food_name,
                    "quantity": float(item.quantity or 1),
                    "serving_unit": item.serving_unit or "serving",
                    "grams": float(item.grams or 0),
                    "calories": round(cal, 1),
                    "protein_g": round(pro, 1),
                    "carbs_g": round(carb, 1),
                    "fat_g": round(fat, 1),
                    "fiber_g": round(fib, 1)
                })

        # 3. Fetch Hydration
        water_stmt = select(Water).where(
            Water.user_id == user_id,
            Water.recorded_at >= start_of_day,
            Water.recorded_at < end_of_day
        )
        water_res = await session.execute(water_stmt)
        water_logs = list(water_res.scalars().all())
        total_water = sum(float(w.amount_ml or 0) for w in water_logs)

        # 4. Fetch Exercise
        ex_stmt = select(Exercise).where(
            Exercise.user_id == user_id,
            Exercise.recorded_at >= start_of_day,
            Exercise.recorded_at < end_of_day
        ).order_by(Exercise.recorded_at.asc())
        ex_res = await session.execute(ex_stmt)
        exercise_logs = list(ex_res.scalars().all())
        total_burned = sum(float(e.calories_burned_est or 0) for e in exercise_logs)
        total_ex_duration = sum(int(e.duration_min or 0) for e in exercise_logs)
        activities = [(getattr(e, "type", None) or getattr(e, "exercise_name", "Workout")).replace("_", " ").title() for e in exercise_logs]
        
        exercise_items_list = []
        for e in exercise_logs:
            act_name = (getattr(e, "type", None) or getattr(e, "exercise_name", "Workout")).replace("_", " ").title()
            time_str = e.recorded_at.strftime("%I:%M %p") if e.recorded_at else ""
            rec_str = e.recorded_at.isoformat() if e.recorded_at else ""
            exercise_items_list.append({
                "id": str(e.id),
                "type": str(e.type or "walking"),
                "activity_name": act_name,
                "duration_min": int(e.duration_min or 0),
                "intensity": str(getattr(e, "intensity", "moderate") or "moderate"),
                "calories_burned": round(float(e.calories_burned_est or 0), 1),
                "time": time_str,
                "recorded_at": rec_str
            })

        # 5. Compute Balances
        total_consumed_cal = round(total_consumed_cal, 1)
        total_consumed_pro = round(total_consumed_pro, 1)
        total_consumed_carb = round(total_consumed_carb, 1)
        total_consumed_fat = round(total_consumed_fat, 1)
        total_consumed_fib = round(total_consumed_fib, 1)
        total_water = round(total_water, 1)
        total_burned = round(total_burned, 1)

        is_over = total_consumed_cal > cal_target
        over_amount = round(total_consumed_cal - cal_target, 1) if is_over else 0.0
        remaining_cal = max(0.0, round(cal_target - total_consumed_cal, 1))
        net_cal = round(total_consumed_cal - total_burned, 1)

        pro_pct = round((total_consumed_pro / pro_target) * 100, 1) if pro_target > 0 else 0.0
        carb_pct = round((total_consumed_carb / carb_target) * 100, 1) if carb_target > 0 else 0.0
        fat_pct = round((total_consumed_fat / fat_target) * 100, 1) if fat_target > 0 else 0.0
        fib_pct = round((total_consumed_fib / fib_target) * 100, 1) if fib_target > 0 else 0.0

        water_pct = round((total_water / water_target) * 100, 1) if water_target > 0 else 0.0
        water_remaining = max(0.0, round(water_target - total_water, 1))

        logged_slots_count = sum(1 for s in slots.values() if s["logged"])
        has_any_data = (len(meals) > 0 or len(water_logs) > 0 or len(exercise_logs) > 0)

        # 6. Meal Slot Summaries
        meals_formatted = {
            "breakfast": {
                "logged": slots["breakfast"]["logged"],
                "status_label": "Logged" if slots["breakfast"]["logged"] else "Not logged",
                "meal_count": len(slots["breakfast"]["items"]),
                "total_calories": round(slots["breakfast"]["calories"], 1),
                "total_protein_g": round(slots["breakfast"]["protein_g"], 1),
                "total_carbs_g": round(slots["breakfast"]["carbs_g"], 1),
                "total_fat_g": round(slots["breakfast"]["fat_g"], 1),
                "total_fiber_g": round(slots["breakfast"]["fiber_g"], 1),
                "items": slots["breakfast"]["items"]
            },
            "lunch": {
                "logged": slots["lunch"]["logged"],
                "status_label": "Logged" if slots["lunch"]["logged"] else "Not logged",
                "meal_count": len(slots["lunch"]["items"]),
                "total_calories": round(slots["lunch"]["calories"], 1),
                "total_protein_g": round(slots["lunch"]["protein_g"], 1),
                "total_carbs_g": round(slots["lunch"]["carbs_g"], 1),
                "total_fat_g": round(slots["lunch"]["fat_g"], 1),
                "total_fiber_g": round(slots["lunch"]["fiber_g"], 1),
                "items": slots["lunch"]["items"]
            },
            "snack": {
                "logged": slots["snack"]["logged"],
                "status_label": "Logged" if slots["snack"]["logged"] else "Not logged",
                "meal_count": len(slots["snack"]["items"]),
                "total_calories": round(slots["snack"]["calories"], 1),
                "total_protein_g": round(slots["snack"]["protein_g"], 1),
                "total_carbs_g": round(slots["snack"]["carbs_g"], 1),
                "total_fat_g": round(slots["snack"]["fat_g"], 1),
                "total_fiber_g": round(slots["snack"]["fiber_g"], 1),
                "items": slots["snack"]["items"]
            },
            "dinner": {
                "logged": slots["dinner"]["logged"],
                "status_label": "Logged" if slots["dinner"]["logged"] else "Not logged",
                "meal_count": len(slots["dinner"]["items"]),
                "total_calories": round(slots["dinner"]["calories"], 1),
                "total_protein_g": round(slots["dinner"]["protein_g"], 1),
                "total_carbs_g": round(slots["dinner"]["carbs_g"], 1),
                "total_fat_g": round(slots["dinner"]["fat_g"], 1),
                "total_fiber_g": round(slots["dinner"]["fiber_g"], 1),
                "items": slots["dinner"]["items"]
            },
            "logged_count": logged_slots_count,
            "total_slots": 4
        }

        # 7. Grounded Daily Insight & Warning Generation via Centralized Status Engine
        has_meals_logged = bool(len(meals) > 0 and total_consumed_cal > 0)
        cal_status_data = NutritionEngine.calculate_calorie_status(
            target_calories=cal_target,
            consumed_calories=total_consumed_cal,
            burned_calories=total_burned,
            fitness_goal=fitness_goal,
            has_meals=has_meals_logged,
            target_includes_activity=True
        )

        goal_status = cal_status_data["status_badge"]
        status_badge = cal_status_data["status_badge"]
        status_level = cal_status_data["status_level"]
        daily_insight = cal_status_data["message"]
        calorie_warning = cal_status_data["warning_message"]
        empty_msg = "No nutrition data has been logged today yet." if not has_any_data else None

        # Add protein note if calories are on track but protein is lagging
        if status_level == "on_track" and total_consumed_pro < (pro_target * 0.7) and logged_slots_count >= 2:
            daily_insight += f" Note: protein intake ({total_consumed_pro}g / {pro_target}g) is lagging; consider a protein-rich food option."

        # 8. Deterministic Daily Progress Score Formula
        # Formula:
        # 1. Calorie adherence (35 pts max): 35 * max(0, 1 - abs(consumed - target)/target)
        # 2. Protein adherence (25 pts max): 25 * min(1.0, consumed / target)
        # 3. Hydration adherence (20 pts max): 20 * min(1.0, water / target)
        # 4. Meal logging consistency (20 pts max): 20 * (logged_slots / 4)
        progress_score = None
        score_explanation = None

        if has_any_data:
            cal_score = 35.0 * max(0.0, 1.0 - (abs(total_consumed_cal - cal_target) / (cal_target or 2000.0)))
            pro_score = 25.0 * min(1.0, (total_consumed_pro / (pro_target or 100.0)))
            water_score = 20.0 * min(1.0, (total_water / (water_target or 2500.0)))
            meal_score = 20.0 * (logged_slots_count / 4.0)

            total_score = int(round(cal_score + pro_score + water_score + meal_score))
            progress_score = max(0, min(100, total_score))
            score_explanation = "Calculated deterministically: 35% calorie balance + 25% protein target + 20% hydration + 20% meal logging completeness."

        display_date_str = parsed_date.strftime("%B %d, %Y")

        return {
            "date": parsed_date.isoformat(),
            "display_date": display_date_str,
            "is_today": is_today,
            "is_future": False,
            "has_data": has_any_data,
            "calories": {
                "target": cal_target,
                "consumed": total_consumed_cal,
                "remaining": remaining_cal,
                "burned": total_burned,
                "net": net_cal,
                "is_over": is_over,
                "over_amount": over_amount
            },
            "macros": {
                "protein": {
                    "target": pro_target,
                    "consumed": total_consumed_pro,
                    "remaining": max(0.0, round(pro_target - total_consumed_pro, 1)),
                    "percentage": pro_pct
                },
                "carbohydrates": {
                    "target": carb_target,
                    "consumed": total_consumed_carb,
                    "remaining": max(0.0, round(carb_target - total_consumed_carb, 1)),
                    "percentage": carb_pct,
                    "is_exceeded": (total_consumed_carb >= carb_target)
                },
                "fat": {
                    "target": fat_target,
                    "consumed": total_consumed_fat,
                    "remaining": max(0.0, round(fat_target - total_consumed_fat, 1)),
                    "percentage": fat_pct
                },
                "fiber": {
                    "target": fib_target,
                    "consumed": total_consumed_fib,
                    "remaining": max(0.0, round(fib_target - total_consumed_fib, 1)),
                    "percentage": fib_pct
                }
            },
            "hydration": {
                "target_ml": water_target,
                "consumed_ml": total_water,
                "remaining_ml": water_remaining,
                "remaining_l": max(0.0, round(water_remaining / 1000.0, 1)),
                "percentage": water_pct,
                "is_zero": (total_water == 0.0)
            },
            "meals": meals_formatted,
            "exercise": {
                "logged": (len(exercise_logs) > 0),
                "duration_minutes": total_ex_duration,
                "calories_burned": total_burned,
                "activities": activities,
                "items": exercise_items_list,
                "message": f"{total_ex_duration} mins, {int(total_burned)} kcal burned" if len(exercise_logs) > 0 else "No exercise logged today."
            },
            "goal": fitness_goal,
            "goal_display": goal_display,
            "goal_status": goal_status,
            "status_level": status_level,
            "status_badge": status_badge,
            "calorie_status": cal_status_data,
            "daily_insight": daily_insight,
            "calorie_warning": calorie_warning,
            "progress_score": progress_score,
            "progress_score_explanation": score_explanation,
            "empty_state_message": empty_msg
        }
