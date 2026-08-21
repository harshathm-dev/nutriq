from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.daily_summary_service import DailySummaryService
from app.utils.date_utils import get_today_local, DEFAULT_TIMEZONE

class WeeklySummaryService:
    @classmethod
    async def get_weekly_summary(
        cls,
        session: AsyncSession,
        user_id: str,
        week_start_str: Optional[str] = None,
        tz_name: str = DEFAULT_TIMEZONE
    ) -> Dict[str, Any]:
        """
        Aggregates the 7-day Weekly Nutrition Summary from daily summaries.
        Architecture: Meal Logs -> Daily Summary -> Weekly Aggregation -> Weekly Summary.
        """
        today_date = get_today_local(tz_name)

        if week_start_str:
            try:
                start_date = date.fromisoformat(week_start_str.split("T")[0])
            except Exception:
                # Default to Monday of current week
                start_date = today_date - timedelta(days=today_date.weekday())
        else:
            # Default to Monday of current week
            start_date = today_date - timedelta(days=today_date.weekday())

        end_date = start_date + timedelta(days=6)
        display_range = f"{start_date.strftime('%b %d')} – {end_date.strftime('%b %d, %Y')}"

        daily_breakdown: List[Dict[str, Any]] = []
        total_cal = 0.0
        total_pro = 0.0
        total_carb = 0.0
        total_fat = 0.0
        total_fib = 0.0
        total_water = 0.0
        total_meals = 0
        total_burned = 0.0
        total_active_mins = 0
        active_days_count = 0
        days_complete = 0
        days_logged = 0
        adherent_days = 0
        elapsed_days = 0

        cal_target = 2000.0
        pro_target = 100.0
        water_target = 2500.0

        best_water_day = None
        max_water_ml = 0.0
        days_over_cal = 0
        days_under_cal = 0

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for i in range(7):
            cur_date = start_date + timedelta(days=i)
            cur_date_str = cur_date.isoformat()
            day_name = day_names[cur_date.weekday()]
            is_today = (cur_date == today_date)
            is_future = (cur_date > today_date)

            if not is_future:
                elapsed_days += 1

            daily_data = await DailySummaryService.get_daily_summary(
                session=session,
                user_id=user_id,
                target_date_str=cur_date_str
            )

            d_cal_target = float(daily_data.get("calories", {}).get("target", 2000.0))
            d_cal_consumed = float(daily_data.get("calories", {}).get("consumed", 0.0)) if not is_future else 0.0
            d_pro_target = float(daily_data.get("macros", {}).get("protein", {}).get("target", 100.0))
            d_pro_consumed = float(daily_data.get("macros", {}).get("protein", {}).get("consumed", 0.0)) if not is_future else 0.0
            d_carb_consumed = float(daily_data.get("macros", {}).get("carbohydrates", {}).get("consumed", 0.0)) if not is_future else 0.0
            d_fat_consumed = float(daily_data.get("macros", {}).get("fat", {}).get("consumed", 0.0)) if not is_future else 0.0
            d_fib_consumed = float(daily_data.get("macros", {}).get("fiber", {}).get("consumed", 0.0)) if not is_future else 0.0
            d_water_target = float(daily_data.get("hydration", {}).get("target_ml", 2500.0))
            d_water_consumed = float(daily_data.get("hydration", {}).get("consumed_ml", 0.0)) if not is_future else 0.0
            d_logged_count = int(daily_data.get("meals", {}).get("logged_count", 0)) if not is_future else 0
            d_burned_cal = float(daily_data.get("exercise", {}).get("calories_burned", 0.0)) if not is_future else 0.0
            d_active_min = int(daily_data.get("exercise", {}).get("duration_minutes", 0)) if not is_future else 0
            d_activities = daily_data.get("exercise", {}).get("activities", []) if not is_future else []

            cal_target = d_cal_target
            pro_target = d_pro_target
            water_target = d_water_target

            b_logged = bool(daily_data.get("meals", {}).get("breakfast", {}).get("logged", False)) if not is_future else False
            l_logged = bool(daily_data.get("meals", {}).get("lunch", {}).get("logged", False)) if not is_future else False
            s_logged = bool(daily_data.get("meals", {}).get("snack", {}).get("logged", False)) if not is_future else False
            d_logged = bool(daily_data.get("meals", {}).get("dinner", {}).get("logged", False)) if not is_future else False

            has_data = (d_logged_count > 0 or d_cal_consumed > 0 or d_burned_cal > 0 or d_water_consumed > 0) and not is_future

            is_complete = (d_logged_count >= 3 or (b_logged and l_logged and d_logged)) if not is_future else False
            if is_complete:
                days_complete += 1

            if has_data:
                days_logged += 1

            if not is_future and (d_burned_cal > 0 or d_active_min > 0):
                active_days_count += 1

            # Calorie adherence within +-15%
            if not is_future and d_cal_consumed > 0:
                if abs(d_cal_consumed - d_cal_target) <= (d_cal_target * 0.15):
                    adherent_days += 1
                if d_cal_consumed > d_cal_target + 50:
                    days_over_cal += 1
                elif d_cal_consumed < d_cal_target - 300:
                    days_under_cal += 1

            if not is_future and d_water_consumed > max_water_ml:
                max_water_ml = d_water_consumed
                best_water_day = day_name

            if not is_future:
                total_cal += d_cal_consumed
                total_pro += d_pro_consumed
                total_carb += d_carb_consumed
                total_fat += d_fat_consumed
                total_fib += d_fib_consumed
                total_water += d_water_consumed
                total_meals += d_logged_count
                total_burned += d_burned_cal
                total_active_mins += d_active_min

            daily_breakdown.append({
                "day_name": day_name,
                "date": cur_date_str,
                "calories_consumed": round(d_cal_consumed, 1),
                "calorie_target": round(d_cal_target, 1),
                "exercise_burned_kcal": round(d_burned_cal, 1),
                "active_minutes": d_active_min,
                "activities": d_activities,
                "protein_consumed_g": round(d_pro_consumed, 1),
                "protein_target_g": round(d_pro_target, 1),
                "carbs_consumed_g": round(d_carb_consumed, 1),
                "fat_consumed_g": round(d_fat_consumed, 1),
                "fiber_consumed_g": round(d_fib_consumed, 1),
                "water_consumed_ml": round(d_water_consumed, 1),
                "water_target_ml": round(d_water_target, 1),
                "meals_logged_count": d_logged_count,
                "is_complete": is_complete,
                "breakfast_logged": b_logged,
                "lunch_logged": l_logged,
                "snack_logged": s_logged,
                "dinner_logged": d_logged,
                "is_today": is_today,
                "is_future": is_future,
                "has_data": has_data,
                "calories": round(d_cal_consumed, 1),
                "protein_g": round(d_pro_consumed, 1),
                "carbs_g": round(d_carb_consumed, 1),
                "fat_g": round(d_fat_consumed, 1),
                "fiber_g": round(d_fib_consumed, 1),
                "water_ml": round(d_water_consumed, 1)
            })

        divisor = float(max(1, elapsed_days)) if elapsed_days > 0 else 7.0
        avg_cal = round(total_cal / divisor, 1) if elapsed_days > 0 else 0.0
        avg_pro = round(total_pro / divisor, 1) if elapsed_days > 0 else 0.0
        avg_carb = round(total_carb / divisor, 1) if elapsed_days > 0 else 0.0
        avg_fat = round(total_fat / divisor, 1) if elapsed_days > 0 else 0.0
        avg_fib = round(total_fib / divisor, 1) if elapsed_days > 0 else 0.0
        avg_water = round(total_water / divisor, 1) if elapsed_days > 0 else 0.0
        avg_burned = round(total_burned / divisor, 1) if elapsed_days > 0 else 0.0

        days_missed = max(0, elapsed_days - days_logged)
        adherence_pct = round((adherent_days / divisor) * 100.0, 1) if elapsed_days > 0 and days_logged > 0 else 0.0
        has_data = (total_cal > 0 or total_water > 0 or total_meals > 0)
        avg_label = f"{elapsed_days}-Day Average" if elapsed_days < 7 and elapsed_days > 0 else "7-Day Average"

        # Rule-based Insights Generation
        insights: List[str] = []
        if not has_data:
            insights.append("Not enough data to generate a weekly summary. Start logging your meals to see weekly trends.")
            empty_state_msg = "Not enough data to generate a weekly summary."
        else:
            empty_state_msg = None
            # Calorie insight
            cal_diff = abs(avg_cal - cal_target)
            if cal_diff <= (cal_target * 0.1):
                insights.append(f"Your average calorie intake ({avg_cal} kcal) was close to your daily target ({cal_target} kcal) this week.")
            elif avg_cal > cal_target:
                insights.append(f"Your average calorie intake ({avg_cal} kcal) exceeded your target by {round(avg_cal - cal_target)} kcal.")
            else:
                insights.append(f"Your average calorie intake ({avg_cal} kcal) was {round(cal_target - avg_cal)} kcal below your daily target.")

            # Logging consistency insight
            insights.append(f"You logged meals on {days_logged} of {elapsed_days} elapsed days ({days_complete} days with complete breakfast, lunch & dinner).")

            # Protein insight
            if avg_pro >= (pro_target * 0.9):
                insights.append(f"Your average protein intake ({avg_pro}g) was consistent with your target ({pro_target}g).")
            else:
                insights.append(f"Your average protein intake ({avg_pro}g) was below your daily target of {pro_target}g.")

            # Hydration insight
            if best_water_day and max_water_ml > 0:
                insights.append(f"Your hydration was highest on {best_water_day} ({round(max_water_ml)} ml).")

            # Days over target insight
            if days_over_cal > 0:
                insights.append(f"Your calorie intake exceeded your target on {days_over_cal} day{'s' if days_over_cal > 1 else ''}.")

        summary_obj = {
            "total_weekly_calories": round(total_cal, 1),
            "avg_daily_calories": avg_cal,
            "calorie_target": round(cal_target, 1),
            "total_protein_g": round(total_pro, 1),
            "avg_protein_g": avg_pro,
            "protein_target_g": round(pro_target, 1),
            "total_carbs_g": round(total_carb, 1),
            "avg_carbs_g": avg_carb,
            "total_fat_g": round(total_fat, 1),
            "avg_fat_g": avg_fat,
            "total_fiber_g": round(total_fib, 1),
            "avg_fiber_g": avg_fib,
            "total_water_ml": round(total_water, 1),
            "avg_water_ml": avg_water,
            "water_target_ml": round(water_target, 1),
            "total_calories_burned": round(total_burned, 1),
            "avg_daily_calories_burned": avg_burned,
            "total_active_minutes": total_active_mins,
            "active_days": f"{active_days_count}/{elapsed_days}",
            "active_days_count": active_days_count,
            "total_meals_logged": total_meals,
            "days_with_complete_logging": days_complete,
            "days_with_missed_meals": days_missed,
            "goal_adherence_pct": adherence_pct,
            "elapsed_days": elapsed_days,
            "avg_label": avg_label
        }

        return {
            "week_start": start_date.isoformat(),
            "week_end": end_date.isoformat(),
            "display_range": display_range,
            "has_data": has_data,
            "summary": summary_obj,
            "daily_breakdown": daily_breakdown,
            "insights": insights,
            "empty_state_message": empty_state_msg
        }
