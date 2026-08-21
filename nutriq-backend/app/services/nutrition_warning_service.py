from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.meal import Meal
from app.models.profile import UserProfile
from app.models.goal import Goal
from app.services.daily_summary_service import DailySummaryService
from app.services.nutrition_engine import NutritionEngine

class NutritionWarningService:
    """
    Personalized Contextual Nutrition Warning & Calorie Status Engine.
    Pure deterministic clinical/behavioral rules grounded in user journal, profile, and goal.
    Zero hallucination, supportive language, and no medical diagnosis claims.
    """

    # Configurable threshold deltas and ratios
    THRESHOLDS = {
        "very_low_ratio": 0.50,       # <50% of target is flagged as Very Low Intake
        "below_target_ratio": 0.85,    # <85% of target is flagged as Below Target
        "weight_loss": {
            "lower_ratio": 0.85,
            "upper_surplus": 50.0,     # > target + 50 kcal is Target Exceeded
            "slight_excess_max": 250.0
        },
        "maintenance": {
            "lower_ratio": 0.85,
            "upper_surplus": 150.0
        },
        "weight_gain": {
            "lower_ratio": 0.85,
            "upper_surplus": 250.0
        },
        "muscle_building": {
            "lower_ratio": 0.85,
            "upper_surplus": 250.0,
            "protein_ratio_min": 0.75
        }
    }

    @classmethod
    def calculate_calorie_status(
        cls,
        target_calories: float,
        consumed_calories: float,
        burned_calories: float = 0.0,
        fitness_goal: str = "weight_loss",
        has_meals: bool = True,
        target_includes_activity: bool = True
    ) -> Dict[str, Any]:
        """
        Centralized, deterministic calorie balance and weight-loss status logic.
        Clearly distinguishes:
        A. Food Consumed
        B. Daily Calorie Target
        C. Physical Activity Calories Burned
        Does NOT subtract exercise from the food target if the target already incorporates activity (TDEE).
        """
        target = round(float(target_calories or 2000.0), 1)
        consumed = round(float(consumed_calories or 0.0), 1)
        burned = round(float(burned_calories or 0.0), 1)
        remaining = max(0.0, round(target - consumed, 1))
        surplus = max(0.0, round(consumed - target, 1))
        percentage = round((consumed / target) * 100.0, 1) if target > 0 else 0.0
        goal_lower = (fitness_goal or "maintain").lower()

        # 0. If no meals logged yet
        if not has_meals or consumed == 0:
            msg = "No meals logged yet today. Log your meals to track your daily calorie balance and progress."
            if burned > 0:
                msg += f" You have also logged {int(burned)} kcal of physical activity."
            return {
                "status": "no_meals",
                "status_level": "no_meals",
                "status_badge": "No Meals Logged Yet",
                "label": "No Meals Logged Yet",
                "message": msg,
                "warning_title": None,
                "warning_message": None,
                "why_it_matters": None,
                "positive_feedback": "Ready to log your first meal today." if burned == 0 else f"You've logged {int(burned)} kcal of physical activity today. Ready to log your meals.",
                "consumed": consumed,
                "target": target,
                "remaining": remaining,
                "burned": burned,
                "percentage": percentage,
                "surplus": 0.0,
                "net_energy_after_exercise": round(consumed - burned, 1)
            }

        # 1. VERY LOW INTAKE: Consumed < 50% of target
        if percentage < (cls.THRESHOLDS["very_low_ratio"] * 100.0):
            status = "very_low"
            status_badge = "Very Low Intake"
            label = "🔴 Very Low Intake"
            warning_title = "Unusually Low Calorie Intake"
            exercise_note = f" You've also logged {int(burned):,} kcal of physical activity." if burned > 0 else ""
            msg = (
                f"Your calorie intake is unusually low today ({int(consumed):,} / {int(target):,} kcal). "
                f"If you haven't finished eating for the day, consider a nourishing meal that supports your daily energy and protein needs.{exercise_note} "
                f"Please consult a qualified nutrition professional for individualized guidance."
            )
            why_matters = "Consistently consuming far below your energy needs can lead to fatigue, nutrient deficiencies, and muscle loss."
            return {
                "status": status,
                "status_level": status,
                "status_badge": status_badge,
                "label": label,
                "message": msg,
                "warning_title": warning_title,
                "warning_message": msg,
                "why_it_matters": why_matters,
                "positive_feedback": None,
                "consumed": consumed,
                "target": target,
                "remaining": remaining,
                "burned": burned,
                "percentage": percentage,
                "surplus": 0.0,
                "net_energy_after_exercise": round(consumed - burned, 1)
            }

        # 2. BELOW TARGET: 50% <= percentage < 85%
        if percentage < (cls.THRESHOLDS["below_target_ratio"] * 100.0):
            status = "below_target"
            status_badge = "Below Today's Target"
            label = "🟡 Below Today's Target"
            warning_title = "Below Today's Target"
            exercise_note = f" You've also logged {int(burned):,} kcal of physical activity." if burned > 0 else ""
            msg = (
                f"You've consumed {int(consumed):,} kcal of your {int(target):,} kcal target ({int(remaining):,} kcal remaining).{exercise_note} "
                f"Consider a balanced meal if you have not finished eating for the day."
            )
            why_matters = "Meeting your intended weight-loss target range ensures steady progress while preserving lean muscle mass and daily energy."
            return {
                "status": status,
                "status_level": status,
                "status_badge": status_badge,
                "label": label,
                "message": msg,
                "warning_title": warning_title,
                "warning_message": msg,
                "why_it_matters": why_matters,
                "positive_feedback": None,
                "consumed": consumed,
                "target": target,
                "remaining": remaining,
                "burned": burned,
                "percentage": percentage,
                "surplus": 0.0,
                "net_energy_after_exercise": round(consumed - burned, 1)
            }

        # 3. TARGET EXCEEDED: Consumed > target + goal_margin
        if "weight_loss" in goal_lower or "fat_loss" in goal_lower:
            excess_margin = cls.THRESHOLDS["weight_loss"]["upper_surplus"]
            goal_desc = "weight-loss"
        elif "maintain" in goal_lower:
            excess_margin = cls.THRESHOLDS["maintenance"]["upper_surplus"]
            goal_desc = "maintenance"
        else:
            excess_margin = cls.THRESHOLDS["weight_gain"]["upper_surplus"]
            goal_desc = "daily"

        if consumed > (target + excess_margin):
            status = "target_exceeded"
            status_badge = "Target Exceeded"
            label = "🟠 Target Exceeded"
            warning_title = "Above Calorie Target"
            msg = f"You've exceeded today's {goal_desc} calorie target by {int(surplus):,} kcal. If this happens consistently, it may make your {goal_desc} goal more difficult."
            why_matters = "A single day of higher intake does not cause immediate weight gain. Focus on hydration, fiber, and nutritional balance for upcoming meals."
            return {
                "status": status,
                "status_level": status,
                "status_badge": status_badge,
                "label": label,
                "message": msg,
                "warning_title": warning_title,
                "warning_message": msg,
                "why_it_matters": why_matters,
                "positive_feedback": None,
                "consumed": consumed,
                "target": target,
                "remaining": 0.0,
                "burned": burned,
                "percentage": percentage,
                "surplus": surplus,
                "net_energy_after_exercise": round(consumed - burned, 1)
            }

        # 4. ON TRACK: 85% <= percentage and consumed <= target + excess_margin
        status = "on_track"
        status_badge = "On Track"
        label = "🟢 On Track"
        exercise_note = f" (along with {int(burned):,} kcal burned from physical activity)" if burned > 0 else ""
        msg = f"You are on track with today's calorie target ({int(consumed):,} / {int(target):,} kcal){exercise_note}."
        positive_fb = f"Great! You're within your calorie target today."
        return {
            "status": status,
            "status_level": status,
            "status_badge": status_badge,
            "label": label,
            "message": msg,
            "warning_title": None,
            "warning_message": None,
            "why_it_matters": None,
            "positive_feedback": positive_fb,
            "consumed": consumed,
            "target": target,
            "remaining": remaining,
            "burned": burned,
            "percentage": percentage,
            "surplus": 0.0,
            "net_energy_after_exercise": round(consumed - burned, 1)
        }

    @classmethod
    async def evaluate_status(
        cls,
        session: AsyncSession,
        user_id: str,
        target_date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates the user's live nutrition status, goal alignment, warnings, and positive feedback.
        """
        daily_summary = await DailySummaryService.get_daily_summary(
            session=session,
            user_id=user_id,
            target_date_str=target_date_str
        )

        cal_consumed = float(daily_summary.get("calories", {}).get("consumed", 0.0))
        cal_target = float(daily_summary.get("calories", {}).get("target", 2000.0))
        cal_burned = float(daily_summary.get("exercise", {}).get("calories_burned", 0.0))
        cal_remaining = float(daily_summary.get("calories", {}).get("remaining", max(0.0, cal_target - cal_consumed)))

        pro_consumed = float(daily_summary.get("macros", {}).get("protein", {}).get("consumed", 0.0))
        pro_target = float(daily_summary.get("macros", {}).get("protein", {}).get("target", 100.0))
        carb_consumed = float(daily_summary.get("macros", {}).get("carbohydrates", {}).get("consumed", 0.0))
        carb_target = float(daily_summary.get("macros", {}).get("carbohydrates", {}).get("target", 250.0))
        fat_consumed = float(daily_summary.get("macros", {}).get("fat", {}).get("consumed", 0.0))
        fat_target = float(daily_summary.get("macros", {}).get("fat", {}).get("target", 60.0))
        fib_consumed = float(daily_summary.get("macros", {}).get("fiber", {}).get("consumed", 0.0))
        fib_target = float(daily_summary.get("macros", {}).get("fiber", {}).get("target", 28.0))

        fitness_goal = str(daily_summary.get("goal", "maintain")).lower()
        goal_display = str(daily_summary.get("goal_display", "Weight Maintenance"))

        has_meals_logged = bool(daily_summary.get("has_data", False) and cal_consumed > 0)

        # 1. Centralized Calorie Status Calculation
        cal_status_data = cls.calculate_calorie_status(
            target_calories=cal_target,
            consumed_calories=cal_consumed,
            burned_calories=cal_burned,
            fitness_goal=fitness_goal,
            has_meals=has_meals_logged,
            target_includes_activity=True
        )

        status_level = cal_status_data["status_level"]
        status_badge = cal_status_data["status_badge"]
        warning_title = cal_status_data["warning_title"]
        warning_message = cal_status_data["warning_message"]
        why_it_matters = cal_status_data["why_it_matters"]
        positive_feedback = cal_status_data["positive_feedback"]

        # 2. Macronutrient Evaluation (Kept separate from calorie status)
        protein_status = "on_track"
        protein_warning = None
        if pro_target > 0:
            pro_pct = (pro_consumed / pro_target) * 100.0
            if pro_pct < 60.0 and cal_consumed >= (cal_target * 0.4):
                protein_status = "below_target"
                protein_warning = f"Your protein intake ({pro_consumed}g / {pro_target}g) is below today's target. Consider adding a protein-rich food option to your next meal."

        # 3. Weekly Pattern Warning Check
        weekly_pattern_warning = None
        try:
            today_date = date.fromisoformat(daily_summary.get("date", date.today().isoformat()))
            excess_days_count = 0
            for day_offset in range(1, 7):
                check_d = today_date - timedelta(days=day_offset)
                past_summary = await DailySummaryService.get_daily_summary(
                    session=session,
                    user_id=user_id,
                    target_date_str=check_d.isoformat()
                )
                p_consumed = float(past_summary.get("calories", {}).get("consumed", 0.0))
                p_target = float(past_summary.get("calories", {}).get("target", 2000.0))
                if p_consumed > (p_target + 50.0):
                    excess_days_count += 1

            if excess_days_count >= 3 and ("weight_loss" in fitness_goal or "fat_loss" in fitness_goal or "maintain" in fitness_goal):
                weekly_pattern_warning = f"Your average calorie intake has been above your target on {excess_days_count} days this week. Consistently exceeding your target may make your goal harder to achieve."
        except Exception:
            weekly_pattern_warning = None

        return {
            "date": daily_summary.get("date", date.today().isoformat()),
            "goal": fitness_goal,
            "goal_display": goal_display,
            "daily_calorie_target": cal_target,
            "calories_consumed": cal_consumed,
            "calories_burned": cal_burned,
            "calories_remaining": cal_remaining,
            "calorie_difference": round(cal_consumed - cal_target, 1),
            "net_energy_after_exercise": round(cal_consumed - cal_burned, 1),
            "status_level": status_level,
            "status_badge": status_badge,
            "calorie_status": cal_status_data,
            "warning_title": warning_title,
            "warning_message": warning_message,
            "why_it_matters": why_it_matters,
            "positive_feedback": positive_feedback,
            "protein_status": protein_status,
            "protein_warning": protein_warning,
            "weekly_pattern_warning": weekly_pattern_warning,
            "has_meals_logged": has_meals_logged,
            "macros": {
                "protein": {"consumed": pro_consumed, "target": pro_target, "remaining": max(0.0, round(pro_target - pro_consumed, 1)), "percentage": round((pro_consumed / pro_target) * 100, 1) if pro_target > 0 else 0.0, "status": protein_status},
                "carbohydrates": {"consumed": carb_consumed, "target": carb_target, "remaining": max(0.0, round(carb_target - carb_consumed, 1)), "percentage": round((carb_consumed / carb_target) * 100, 1) if carb_target > 0 else 0.0},
                "fat": {"consumed": fat_consumed, "target": fat_target, "remaining": max(0.0, round(fat_target - fat_consumed, 1)), "percentage": round((fat_consumed / fat_target) * 100, 1) if fat_target > 0 else 0.0},
                "fiber": {"consumed": fib_consumed, "target": fib_target, "remaining": max(0.0, round(fib_target - fib_consumed, 1)), "percentage": round((fib_consumed / fib_target) * 100, 1) if fib_target > 0 else 0.0}
            }
        }

    @classmethod
    async def generate_nutrition_insights(
        cls,
        session: AsyncSession,
        user_id: str,
        target_date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates dynamic, non-static, data-grounded nutrition insights for the user.
        Calculates insights from actual database numbers (calories, macros, water, goals).
        Guards against false low-calorie warnings at midnight when 0 meals are logged.
        """
        daily_summary = await DailySummaryService.get_daily_summary(
            session=session,
            user_id=user_id,
            target_date_str=target_date_str
        )

        has_data = daily_summary.get("has_data", False)
        cal = daily_summary.get("calories", {})
        macros = daily_summary.get("macros", {})
        hyd = daily_summary.get("hydration", {})
        goal = daily_summary.get("goal_display", "Weight Loss")

        consumed_cal = float(cal.get("consumed", 0.0))
        target_cal = float(cal.get("target", 2000.0))
        remaining_cal = float(cal.get("remaining", target_cal))

        pro = macros.get("protein", {})
        consumed_pro = float(pro.get("consumed", 0.0))
        target_pro = float(pro.get("target", 100.0))

        carb = macros.get("carbohydrates", {})
        consumed_carb = float(carb.get("consumed", 0.0))
        target_carb = float(carb.get("target", 250.0))

        fib = macros.get("fiber", {})
        consumed_fib = float(fib.get("consumed", 0.0))
        target_fib = float(fib.get("target", 28.0))

        consumed_water = float(hyd.get("consumed_ml", 0.0))
        target_water = float(hyd.get("target_ml", 2500.0))

        insights_cards: List[Dict[str, Any]] = []

        if not has_data or consumed_cal == 0:
            insights_cards.append({
                "id": "no_meals_today",
                "type": "info",
                "variant": "blue",
                "title": "Ready for Today's Meals",
                "message": f"Log your breakfast or first meal to see dynamic insights calculated for your {goal} plan.",
                "metric": f"{int(target_cal):,} kcal budget",
                "icon": "sparkles"
            })
            return {
                "date": daily_summary.get("date"),
                "display_date": daily_summary.get("display_date"),
                "has_data": False,
                "goal": goal,
                "summary": f"Your daily calorie budget is {int(target_cal):,} kcal. Start logging meals to view your progress.",
                "insights": insights_cards,
                "calorie_status": "no_meals",
                "protein_status": "not_started",
                "hydration_status": "not_started"
            }

        # 1. Calorie Insight
        if consumed_cal > target_cal + 50:
            over = int(consumed_cal - target_cal)
            insights_cards.append({
                "id": "cal_over",
                "type": "warning",
                "variant": "amber",
                "title": "Calorie Target Exceeded",
                "message": f"You are {over:,} kcal above your daily target. Consider choosing lighter, high-fiber dinner or snack options.",
                "metric": f"+{over:,} kcal over",
                "icon": "alert"
            })
            cal_status = "exceeded"
        elif consumed_cal >= target_cal * 0.85:
            insights_cards.append({
                "id": "cal_ontrack",
                "type": "success",
                "variant": "emerald",
                "title": "Calorie Budget On Track",
                "message": f"You've consumed {int(consumed_cal):,} kcal of your {int(target_cal):,} kcal budget ({int(remaining_cal):,} kcal remaining).",
                "metric": f"{int(remaining_cal):,} kcal left",
                "icon": "check"
            })
            cal_status = "on_track"
        else:
            insights_cards.append({
                "id": "cal_deficit",
                "type": "info",
                "variant": "cyan",
                "title": "Healthy Deficit",
                "message": f"You currently have {int(remaining_cal):,} kcal remaining for the rest of today.",
                "metric": f"{int(remaining_cal):,} kcal left",
                "icon": "flame"
            })
            cal_status = "deficit"

        # 2. Protein Insight
        if target_pro > 0:
            if consumed_pro >= target_pro * 0.9:
                insights_cards.append({
                    "id": "pro_achieved",
                    "type": "success",
                    "variant": "emerald",
                    "title": "Protein Goal Achieved",
                    "message": f"Great job! You logged {consumed_pro}g protein, meeting your daily target for muscle preservation.",
                    "metric": f"{consumed_pro}g / {target_pro}g",
                    "icon": "check"
                })
                pro_status = "achieved"
            elif consumed_pro < target_pro * 0.5 and consumed_cal >= target_cal * 0.5:
                pro_rem = round(target_pro - consumed_pro, 1)
                insights_cards.append({
                    "id": "pro_low",
                    "type": "warning",
                    "variant": "amber",
                    "title": "Protein Intake is Low",
                    "message": f"You need {pro_rem}g more protein today. Try adding paneer, eggs, chicken, or lentils to your next meal.",
                    "metric": f"{pro_rem}g needed",
                    "icon": "alert"
                })
                pro_status = "low"
            else:
                pro_rem = round(target_pro - consumed_pro, 1)
                insights_cards.append({
                    "id": "pro_progress",
                    "type": "info",
                    "variant": "blue",
                    "title": "Protein Progress",
                    "message": f"You have logged {consumed_pro}g protein ({pro_rem}g remaining to reach your target).",
                    "metric": f"{consumed_pro}g logged",
                    "icon": "trending-up"
                })
                pro_status = "in_progress"
        else:
            pro_status = "not_set"

        # 3. Hydration Insight
        if target_water > 0:
            if consumed_water >= target_water:
                insights_cards.append({
                    "id": "water_goal",
                    "type": "success",
                    "variant": "cyan",
                    "title": "Hydration Target Reached",
                    "message": f"Excellent hydration! You have logged {int(consumed_water):,} ml water today.",
                    "metric": f"{int(consumed_water):,} ml",
                    "icon": "droplet"
                })
                water_status = "achieved"
            elif consumed_water < target_water * 0.5:
                w_rem = int(target_water - consumed_water)
                insights_cards.append({
                    "id": "water_low",
                    "type": "info",
                    "variant": "cyan",
                    "title": "Hydration Reminder",
                    "message": f"You have logged {int(consumed_water):,} ml water. Drink {w_rem:,} ml more to reach your target.",
                    "metric": f"{w_rem:,} ml left",
                    "icon": "droplet"
                })
                water_status = "low"
            else:
                water_status = "in_progress"
        else:
            water_status = "not_set"

        # 4. Fiber Insight
        if consumed_fib >= target_fib:
            insights_cards.append({
                "id": "fiber_high",
                "type": "success",
                "variant": "emerald",
                "title": "High Dietary Fiber",
                "message": f"You have reached {consumed_fib}g dietary fiber today, supporting excellent digestion and satiety.",
                "metric": f"{consumed_fib}g fiber",
                "icon": "sparkles"
            })

        summary_msg = f"You have consumed {int(consumed_cal):,} of {int(target_cal):,} kcal with {consumed_pro}g protein logged for your {goal} plan."

        return {
            "date": daily_summary.get("date"),
            "display_date": daily_summary.get("display_date"),
            "has_data": True,
            "goal": goal,
            "summary": summary_msg,
            "insights": insights_cards,
            "calorie_status": cal_status,
            "protein_status": pro_status,
            "hydration_status": water_status,
            "consumed": {
                "calories": consumed_cal,
                "protein_g": consumed_pro,
                "carbs_g": consumed_carb,
                "fat_g": consumed_fat,
                "fiber_g": consumed_fib,
                "water_ml": consumed_water
            },
            "targets": {
                "calories": target_cal,
                "protein_g": target_pro,
                "carbs_g": target_carb,
                "fat_g": target_fat,
                "fiber_g": target_fib,
                "water_ml": target_water
            }
        }

