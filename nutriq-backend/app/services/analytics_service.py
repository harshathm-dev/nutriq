from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, date, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.meal import Meal, MealItem
from app.models.tracking import Water, Exercise, WeightHistory
from app.models.profile import UserProfile
from app.models.goal import Goal
from app.services.nutrition_engine import NutritionEngine
from app.utils.date_utils import (
    get_date_bounds_utc,
    get_today_local,
    get_local_date,
    DEFAULT_TIMEZONE
)

class AnalyticsService:
    @classmethod
    async def get_daily_analytics(
        cls,
        session: AsyncSession,
        user_id: str,
        target_date: Any,
        tz_name: str = DEFAULT_TIMEZONE
    ) -> Dict[str, Any]:
        if isinstance(target_date, datetime):
            target_d = get_local_date(target_date, tz_name)
        elif isinstance(target_date, date):
            target_d = target_date
        elif isinstance(target_date, str):
            try:
                target_d = date.fromisoformat(target_date.split("T")[0])
            except Exception:
                target_d = get_today_local(tz_name)
        else:
            target_d = get_today_local(tz_name)

        start_utc, end_utc = get_date_bounds_utc(target_d, tz_name)

        # Get meals
        meal_stmt = select(Meal).where(
            Meal.user_id == user_id,
            Meal.occurred_at >= start_utc,
            Meal.occurred_at < end_utc
        ).options(selectinload(Meal.items))
        meal_res = await session.execute(meal_stmt)
        meals = list(meal_res.scalars().all())

        consumed_cal = sum(sum(float(i.calories or 0) for i in m.items) for m in meals)
        consumed_pro = sum(sum(float(i.protein_g or 0) for i in m.items) for m in meals)
        consumed_carb = sum(sum(float(i.carbs_g or 0) for i in m.items) for m in meals)
        consumed_fat = sum(sum(float(i.fat_g or 0) for i in m.items) for m in meals)
        consumed_fib = sum(sum(float(i.fiber_g or 0) for i in m.items) for m in meals)
        consumed_sug = sum(sum(float(i.sugar_g or 0) for i in m.items) for m in meals)
        consumed_sod = sum(sum(float(i.sodium_mg or 0) for i in m.items) for m in meals)

        # Get water
        water_stmt = select(Water).where(
            Water.user_id == user_id,
            Water.recorded_at >= start_utc,
            Water.recorded_at < end_utc
        )
        water_res = await session.execute(water_stmt)
        water_logs = list(water_res.scalars().all())
        total_water = sum(float(w.amount_ml or 0) for w in water_logs)

        # Get exercise
        ex_stmt = select(Exercise).where(
            Exercise.user_id == user_id,
            Exercise.recorded_at >= start_utc,
            Exercise.recorded_at < end_utc
        )
        ex_res = await session.execute(ex_stmt)
        exercise_logs = list(ex_res.scalars().all())
        total_burned = sum(float(e.calories_burned_est or 0) for e in exercise_logs)

        # Get targets
        prof_stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        prof_res = await session.execute(prof_stmt)
        prof = prof_res.scalar_one_or_none()

        goal_stmt = select(Goal).where(Goal.user_id == user_id, Goal.active == True)
        goal_res = await session.execute(goal_stmt)
        goal = goal_res.scalar_one_or_none()

        if prof and goal:
            targets = NutritionEngine.calculate_targets(
                weight_kg=prof.weight_kg,
                height_cm=prof.height_cm,
                age=prof.age,
                gender=prof.gender,
                activity_level=prof.activity_level,
                fitness_goal=goal.goal_type,
                desired_rate=goal.desired_rate,
                dietary_preference=prof.dietary_preference
            )
        elif prof:
            targets = NutritionEngine.calculate_targets(
                weight_kg=prof.weight_kg,
                height_cm=prof.height_cm,
                age=prof.age,
                gender=prof.gender,
                activity_level=prof.activity_level,
                fitness_goal=prof.fitness_goal,
                desired_rate=0.5,
                dietary_preference=prof.dietary_preference
            )
        else:
            targets = {
                "target_calories": 2000.0,
                "protein_g": 100.0,
                "carbs_g": 250.0,
                "fat_g": 60.0,
                "fiber_g": 28.0,
                "water_ml": 2500.0,
                "bmr": 1600.0,
                "tdee": 2200.0
            }

        net_calories = consumed_cal - total_burned
        remaining_cal = max(0.0, targets["target_calories"] - consumed_cal)

        return {
            "date": target_d.isoformat(),
            "targets": targets,
            "consumed": {
                "calories": round(consumed_cal, 1),
                "protein_g": round(consumed_pro, 1),
                "carbs_g": round(consumed_carb, 1),
                "fat_g": round(consumed_fat, 1),
                "fiber_g": round(consumed_fib, 1),
                "sugar_g": round(consumed_sug, 1),
                "sodium_mg": round(consumed_sod, 1),
                "water_ml": round(total_water, 1),
                "burned_calories": round(total_burned, 1),
                "net_calories": round(net_calories, 1),
                "remaining_calories": round(remaining_cal, 1)
            },
            "meal_count": len(meals)
        }

    @classmethod
    async def get_analytics_range(
        cls,
        session: AsyncSession,
        user_id: str,
        range_key: str = "7d",
        start_date_str: Optional[str] = None,
        end_date_str: Optional[str] = None,
        tz_name: str = DEFAULT_TIMEZONE
    ) -> Dict[str, Any]:
        today_local = get_today_local(tz_name)

        # 1. Resolve start and end dates
        if start_date_str and end_date_str:
            try:
                start_date = date.fromisoformat(start_date_str.split("T")[0])
                end_date = date.fromisoformat(end_date_str.split("T")[0])
                if start_date > end_date:
                    start_date, end_date = end_date, start_date
                range_label = f"{start_date.isoformat()} to {end_date.isoformat()}"
            except Exception:
                start_date = today_local - timedelta(days=6)
                end_date = today_local
                range_label = "7d"
        else:
            range_clean = (range_key or "7d").lower()
            if range_clean in ["30d", "month", "30_days", "30"]:
                start_date = today_local - timedelta(days=29)
                end_date = today_local
                range_label = "30d"
            elif range_clean in ["90d", "quarter", "90_days", "90"]:
                start_date = today_local - timedelta(days=89)
                end_date = today_local
                range_label = "90d"
            else:
                start_date = today_local - timedelta(days=6)
                end_date = today_local
                range_label = "7d"

        total_period_days = (end_date - start_date).days + 1

        # 2. Fetch User Profile and Goals for targets
        prof_stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        prof_res = await session.execute(prof_stmt)
        prof = prof_res.scalar_one_or_none()

        goal_stmt = select(Goal).where(Goal.user_id == user_id, Goal.active == True)
        goal_res = await session.execute(goal_stmt)
        goal = goal_res.scalar_one_or_none()

        if prof and goal:
            calculated_targets = NutritionEngine.calculate_targets(
                weight_kg=prof.weight_kg,
                height_cm=prof.height_cm,
                age=prof.age,
                gender=prof.gender,
                activity_level=prof.activity_level,
                fitness_goal=goal.goal_type,
                desired_rate=goal.desired_rate,
                dietary_preference=prof.dietary_preference
            )
        elif prof:
            calculated_targets = NutritionEngine.calculate_targets(
                weight_kg=prof.weight_kg,
                height_cm=prof.height_cm,
                age=prof.age,
                gender=prof.gender,
                activity_level=prof.activity_level,
                fitness_goal=prof.fitness_goal,
                desired_rate=0.5,
                dietary_preference=prof.dietary_preference
            )
        else:
            calculated_targets = {
                "target_calories": 2000.0,
                "protein_g": 100.0,
                "carbs_g": 250.0,
                "fat_g": 60.0,
                "fiber_g": 28.0,
                "water_ml": 2500.0
            }

        target_cal = round(float(calculated_targets.get("target_calories", 2000.0)), 1)
        target_pro = round(float(calculated_targets.get("protein_g", 100.0)), 1)
        target_carb = round(float(calculated_targets.get("carbs_g", 250.0)), 1)
        target_fat = round(float(calculated_targets.get("fat_g", 60.0)), 1)
        target_fib = round(float(calculated_targets.get("fiber_g", 28.0)), 1)
        target_water_ml = round(float(calculated_targets.get("water_ml", 2500.0)), 1)
        target_water_l = round(target_water_ml / 1000.0, 2)

        # 3. Iterate through date range
        calories_series = []
        hydration_series = []
        macros_series = []
        protein_series = []
        activity_series = []
        calorie_balance_series = []

        total_consumed_cal = 0.0
        total_consumed_pro = 0.0
        total_consumed_carb = 0.0
        total_consumed_fat = 0.0
        total_consumed_fib = 0.0
        total_water_ml = 0.0
        total_burned_cal = 0.0
        total_active_minutes = 0
        total_steps = 0

        days_with_meals = 0
        days_with_water = 0
        days_with_activity = 0
        days_goal_achieved_water = 0
        days_goal_met_protein = 0
        days_adherence_count = 0

        best_hydration_day = None
        max_water_ml = -1.0
        most_active_day = None
        max_burned_cal = -1.0

        for i in range(total_period_days):
            cur_date = start_date + timedelta(days=i)
            display_date = cur_date.strftime("%b %d")
            weekday_name = cur_date.strftime("%A")

            start_utc, end_utc = get_date_bounds_utc(cur_date, tz_name)

            # Query Meals
            meal_stmt = select(Meal).where(
                Meal.user_id == user_id,
                Meal.occurred_at >= start_utc,
                Meal.occurred_at < end_utc
            ).options(selectinload(Meal.items))
            meal_res = await session.execute(meal_stmt)
            meals = list(meal_res.scalars().all())

            # Query Water
            water_stmt = select(Water).where(
                Water.user_id == user_id,
                Water.recorded_at >= start_utc,
                Water.recorded_at < end_utc
            )
            water_res = await session.execute(water_stmt)
            water_logs = list(water_res.scalars().all())

            # Query Exercise
            ex_stmt = select(Exercise).where(
                Exercise.user_id == user_id,
                Exercise.recorded_at >= start_utc,
                Exercise.recorded_at < end_utc
            )
            ex_res = await session.execute(ex_stmt)
            exercise_logs = list(ex_res.scalars().all())

            # Daily Calorie & Macro Sums
            d_cal = 0.0
            d_pro = 0.0
            d_carb = 0.0
            d_fat = 0.0
            d_fib = 0.0

            for m in meals:
                for item in m.items:
                    d_cal += float(item.calories or 0)
                    d_pro += float(item.protein_g or 0)
                    d_carb += float(item.carbs_g or 0)
                    d_fat += float(item.fat_g or 0)
                    d_fib += float(item.fiber_g or 0)

            # Daily Water Sum
            d_water_ml = sum(float(w.amount_ml or 0) for w in water_logs)
            d_water_l = round(d_water_ml / 1000.0, 2)

            # Daily Exercise Sum
            d_burned = sum(float(e.calories_burned_est or 0) for e in exercise_logs)
            d_duration = sum(int(e.duration_min or 0) for e in exercise_logs)
            d_steps = sum(int(e.steps or 0) for e in exercise_logs)
            d_distance = sum(float(e.distance_km or 0.0) for e in exercise_logs)

            has_meals = len(meals) > 0
            has_water = len(water_logs) > 0
            has_activity = len(exercise_logs) > 0
            is_tracked = has_meals or has_water or has_activity

            if has_meals:
                days_with_meals += 1
                total_consumed_cal += d_cal
                total_consumed_pro += d_pro
                total_consumed_carb += d_carb
                total_consumed_fat += d_fat
                total_consumed_fib += d_fib

                # Calorie Status
                if d_cal >= target_cal * 0.85 and d_cal <= target_cal * 1.15:
                    status = "target"
                    days_adherence_count += 1
                elif d_cal < target_cal * 0.85:
                    status = "under"
                else:
                    status = "over"
            else:
                status = "unlogged"

            if has_water:
                days_with_water += 1
                total_water_ml += d_water_ml
                if d_water_ml >= target_water_ml * 0.9:
                    days_goal_achieved_water += 1

                if d_water_ml > max_water_ml and d_water_ml > 0:
                    max_water_ml = d_water_ml
                    best_hydration_day = {
                        "date": cur_date.isoformat(),
                        "display_date": display_date,
                        "liters": d_water_l,
                        "ml": d_water_ml
                    }

            if d_pro >= target_pro * 0.9 and has_meals:
                days_goal_met_protein += 1

            if has_activity:
                days_with_activity += 1
                total_burned_cal += d_burned
                total_active_minutes += d_duration
                total_steps += d_steps

                if d_burned > max_burned_cal and d_burned > 0:
                    max_burned_cal = d_burned
                    most_active_day = {
                        "date": cur_date.isoformat(),
                        "display_date": weekday_name,
                        "calories": round(d_burned, 1),
                        "duration": d_duration
                    }

            # 1. Calorie series
            diff_cal = round(d_cal - target_cal, 1)
            calories_series.append({
                "date": cur_date.isoformat(),
                "display_date": display_date,
                "consumed": round(d_cal, 1),
                "target": target_cal,
                "diff": diff_cal,
                "status": status,
                "is_tracked": has_meals
            })

            # 2. Hydration series
            hydration_series.append({
                "date": cur_date.isoformat(),
                "display_date": display_date,
                "consumed_liters": d_water_l,
                "consumed_ml": round(d_water_ml, 1),
                "target_liters": target_water_l,
                "target_ml": target_water_ml,
                "goal_achieved": (d_water_ml >= target_water_ml * 0.9) and has_water,
                "is_tracked": has_water
            })

            # 3. Macro series
            pro_pct = round((d_pro * 4.0 / d_cal) * 100, 1) if d_cal > 0 else 0.0
            carb_pct = round((d_carb * 4.0 / d_cal) * 100, 1) if d_cal > 0 else 0.0
            fat_pct = round((d_fat * 9.0 / d_cal) * 100, 1) if d_cal > 0 else 0.0
            macros_series.append({
                "date": cur_date.isoformat(),
                "display_date": display_date,
                "protein_g": round(d_pro, 1),
                "carbs_g": round(d_carb, 1),
                "fat_g": round(d_fat, 1),
                "fiber_g": round(d_fib, 1),
                "calories": round(d_cal, 1),
                "protein_pct": pro_pct,
                "carbs_pct": carb_pct,
                "fat_pct": fat_pct,
                "is_tracked": has_meals
            })

            # 4. Protein series
            pro_achieved = round((d_pro / target_pro) * 100, 1) if target_pro > 0 and has_meals else 0.0
            protein_series.append({
                "date": cur_date.isoformat(),
                "display_date": display_date,
                "consumed_g": round(d_pro, 1),
                "target_g": target_pro,
                "achieved_pct": pro_achieved,
                "is_tracked": has_meals
            })

            # 5. Activity series
            activity_series.append({
                "date": cur_date.isoformat(),
                "display_date": display_date,
                "calories_burned": round(d_burned, 1),
                "duration_minutes": d_duration,
                "steps": d_steps,
                "distance_km": round(d_distance, 2),
                "has_activity": has_activity
            })

            # 6. Calorie balance series
            d_net = round(d_cal - d_burned, 1)
            calorie_balance_series.append({
                "date": cur_date.isoformat(),
                "display_date": display_date,
                "intake": round(d_cal, 1),
                "burned": round(d_burned, 1),
                "net": d_net,
                "target": target_cal,
                "is_tracked": is_tracked
            })

        # 4. Calculate True Averages across Tracked Days (or full period if all active)
        divisor_cal = max(1, days_with_meals)
        avg_calories = round(total_consumed_cal / divisor_cal, 1) if days_with_meals > 0 else 0.0
        avg_protein = round(total_consumed_pro / divisor_cal, 1) if days_with_meals > 0 else 0.0
        avg_carbs = round(total_consumed_carb / divisor_cal, 1) if days_with_meals > 0 else 0.0
        avg_fat = round(total_consumed_fat / divisor_cal, 1) if days_with_meals > 0 else 0.0
        avg_fiber = round(total_consumed_fib / divisor_cal, 1) if days_with_meals > 0 else 0.0

        divisor_water = max(1, days_with_water)
        avg_water_ml = round(total_water_ml / divisor_water, 1) if days_with_water > 0 else 0.0
        avg_water_l = round(avg_water_ml / 1000.0, 2)

        divisor_act = max(1, days_with_activity)
        avg_burned = round(total_burned_cal / divisor_act, 1) if days_with_activity > 0 else 0.0

        # Goal adherence calculation (% of tracked days meeting calorie target within 15%)
        adherence_pct = round((days_adherence_count / divisor_cal) * 100, 1) if days_with_meals > 0 else 0.0

        # 5. Compute Previous Period for comparison (Card 1 comparison % vs previous period)
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=total_period_days - 1)
        prev_start_utc, prev_end_utc = get_date_bounds_utc(prev_start_date, tz_name)[0], get_date_bounds_utc(prev_end_date, tz_name)[1]

        prev_meal_stmt = select(Meal).where(
            Meal.user_id == user_id,
            Meal.occurred_at >= prev_start_utc,
            Meal.occurred_at < prev_end_utc
        ).options(selectinload(Meal.items))
        prev_meal_res = await session.execute(prev_meal_stmt)
        prev_meals = list(prev_meal_res.scalars().all())

        prev_cal_sum = 0.0
        prev_active_days = set()
        for m in prev_meals:
            for item in m.items:
                prev_cal_sum += float(item.calories or 0)
            if m.occurred_at:
                prev_active_days.add(get_local_date(m.occurred_at, tz_name))

        prev_divisor = max(1, len(prev_active_days))
        prev_avg_calories = round(prev_cal_sum / prev_divisor, 1) if len(prev_active_days) > 0 else None

        calorie_change_pct = None
        if prev_avg_calories is not None and prev_avg_calories > 0 and avg_calories > 0:
            calorie_change_pct = round(((avg_calories - prev_avg_calories) / prev_avg_calories) * 100, 1)

        # 6. Weight Progress from SQLite
        weight_stmt = select(WeightHistory).where(
            WeightHistory.user_id == user_id
        ).order_by(WeightHistory.recorded_at.asc())
        w_res = await session.execute(weight_stmt)
        all_weights = list(w_res.scalars().all())

        weight_history_points = []
        for w in all_weights:
            rec_date = get_local_date(w.recorded_at, tz_name)
            weight_history_points.append({
                "date": rec_date.isoformat(),
                "display_date": rec_date.strftime("%b %d"),
                "weight_kg": round(w.weight_kg, 1),
                "recorded_at": w.recorded_at.isoformat() if w.recorded_at else None
            })

        current_weight = prof.weight_kg if prof and prof.weight_kg else (weight_history_points[-1]["weight_kg"] if weight_history_points else None)
        target_weight = goal.target_weight_kg if goal and goal.target_weight_kg else None
        starting_weight = weight_history_points[0]["weight_kg"] if weight_history_points else current_weight
        weight_change = round(current_weight - starting_weight, 1) if (current_weight and starting_weight) else None

        # 7. Generate Grounded Nutrition Insights
        insights = []
        has_any_data = days_with_meals > 0 or days_with_water > 0 or days_with_activity > 0 or len(weight_history_points) > 0

        # Calorie Insight
        over_target_days = sum(1 for c in calories_series if c["status"] == "over")
        under_target_days = sum(1 for c in calories_series if c["status"] == "under")
        on_target_days = sum(1 for c in calories_series if c["status"] == "target")

        if days_with_meals > 0:
            cal_diff = round(avg_calories - target_cal)
            if abs(cal_diff) <= target_cal * 0.05:
                cal_insight = "Your average calorie intake is closely aligned with your daily target."
            elif cal_diff < 0:
                cal_insight = f"Your average intake is {abs(cal_diff)} kcal below your daily target."
            else:
                cal_insight = f"Your average intake is {cal_diff} kcal above your daily target."

            if over_target_days > 0:
                insights.append(f"You exceeded your calorie target on {over_target_days} of the last {total_period_days} days.")
            elif on_target_days >= max(1, days_with_meals // 2):
                insights.append("Great consistency! Your calorie intake is well-controlled within your target range.")
            insights.append(cal_insight)
        else:
            cal_insight = "Start logging meals to track your daily calorie intake vs target."

        # Hydration Insight
        if days_with_water > 0:
            hydration_insight_text = f"Hydration goal achieved on {days_goal_achieved_water} of {total_period_days} days."
            insights.append(hydration_insight_text)
            if avg_water_l >= target_water_l:
                insights.append(f"Optimal hydration! Averaging {avg_water_l}L daily exceeding your {target_water_l}L goal.")
            else:
                insights.append(f"Aim to increase daily water intake by {round(target_water_l - avg_water_l, 1)}L to meet your {target_water_l}L goal.")
        else:
            hydration_insight_text = "No water logs recorded yet. Start tracking hydration."

        # Protein Insight
        if days_with_meals > 0:
            if avg_protein >= target_pro * 0.9:
                insights.append(f"Excellent protein intake! You achieved {avg_protein}g/day against your {target_pro}g goal.")
            else:
                insights.append(f"Protein intake is below target on {total_period_days - days_goal_met_protein} days. Consider incorporating high-protein foods.")

        # Activity Insight
        if most_active_day and days_with_activity > 0:
            insights.append(f"Your most active day was {most_active_day['display_date']} with {most_active_day['calories']} kcal burned.")

        if not has_any_data:
            insights = ["Start logging meals, water, and activities to unlock personalized nutrition intelligence."]

        # Macro percentages
        total_macro_cal = (avg_protein * 4.0) + (avg_carbs * 4.0) + (avg_fat * 9.0)
        p_pct = round((avg_protein * 4.0 / total_macro_cal) * 100, 1) if total_macro_cal > 0 else 0.0
        c_pct = round((avg_carbs * 4.0 / total_macro_cal) * 100, 1) if total_macro_cal > 0 else 0.0
        f_pct = round((avg_fat * 9.0 / total_macro_cal) * 100, 1) if total_macro_cal > 0 else 0.0

        return {
            "range": range_label,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "summary": {
                "avg_calories": avg_calories,
                "prev_avg_calories": prev_avg_calories,
                "calorie_change_pct": calorie_change_pct,
                "target_calories": target_cal,
                "avg_protein": avg_protein,
                "target_protein": target_pro,
                "avg_water_liters": avg_water_l,
                "target_water_liters": target_water_l,
                "goal_adherence_pct": adherence_pct,
                "total_tracked_days": days_with_meals,
                "total_period_days": total_period_days,
                "has_data": has_any_data
            },
            "calories": calories_series,
            "calorie_insight": cal_insight,
            "hydration": hydration_series,
            "hydration_summary": {
                "avg_liters": avg_water_l,
                "target_liters": target_water_l,
                "best_day": best_hydration_day,
                "days_goal_achieved": days_goal_achieved_water,
                "total_days": total_period_days,
                "insight": hydration_insight_text
            },
            "macros": macros_series,
            "macro_averages": {
                "avg_protein_g": avg_protein,
                "avg_carbs_g": avg_carbs,
                "avg_fat_g": avg_fat,
                "avg_fiber_g": avg_fiber,
                "protein_calories_pct": p_pct,
                "carbs_calories_pct": c_pct,
                "fat_calories_pct": f_pct
            },
            "protein": protein_series,
            "protein_summary": {
                "avg_protein": avg_protein,
                "target_protein": target_pro,
                "achievement_pct": round((avg_protein / target_pro) * 100, 1) if target_pro > 0 else 0.0,
                "days_met": days_goal_met_protein,
                "total_days": total_period_days
            },
            "activity": activity_series,
            "activity_summary": {
                "total_calories_burned": round(total_burned_cal, 1),
                "total_duration_minutes": total_active_minutes,
                "avg_calories_burned": avg_burned,
                "total_steps": total_steps,
                "most_active_day": most_active_day
            },
            "calorie_balance": calorie_balance_series,
            "weight_progress": {
                "current_weight_kg": current_weight,
                "target_weight_kg": target_weight,
                "starting_weight_kg": starting_weight,
                "weight_change_kg": weight_change,
                "has_history": len(weight_history_points) > 0,
                "history": weight_history_points
            },
            "nutrition_insights": insights
        }
