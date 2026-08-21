from typing import Dict, Any
from app.config import settings

class NutritionEngine:
    """
    Deterministic Nutrition Calculation Engine
    Implements Mifflin-St Jeor equation and standard clinical reference rules.
    Zero LLM dependency.
    """

    ACTIVITY_MULTIPLIERS = {
        "sedentary": 1.20,
        "lightly_active": 1.375,
        "moderately_active": 1.55,
        "very_active": 1.725,
        "extremely_active": 1.90
    }

    GOAL_ADJUSTMENTS = {
        "weight_loss": -500.0,      # ~0.5kg/week deficit
        "maintain": 0.0,
        "weight_gain": 400.0,       # ~0.4kg/week surplus
        "muscle_building": 250.0    # lean surplus with high protein
    }

    @classmethod
    def calculate_bmr(cls, weight_kg: float, height_cm: float, age: int, gender: str) -> float:
        """
        Mifflin-St Jeor Formula:
        Men: BMR = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
        Women: BMR = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
        Other: average of male and female formula (-78)
        """
        base = (10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age)
        gender_lower = gender.lower()
        if gender_lower in ["male", "m", "man"]:
            return round(base + 5.0, 2)
        elif gender_lower in ["female", "f", "woman"]:
            return round(base - 161.0, 2)
        else:
            return round(base - 78.0, 2)

    @classmethod
    def calculate_tdee(cls, bmr: float, activity_level: str) -> float:
        multiplier = cls.ACTIVITY_MULTIPLIERS.get(activity_level.lower(), 1.55)
        return round(bmr * multiplier, 2)

    @classmethod
    def calculate_targets(
        cls,
        weight_kg: float,
        height_cm: float,
        age: int,
        gender: str,
        activity_level: str = "moderately_active",
        fitness_goal: str = "maintain",
        desired_rate: float = 0.5,
        dietary_preference: str = "standard"
    ) -> Dict[str, Any]:
        bmr = cls.calculate_bmr(weight_kg, height_cm, age, gender)
        multiplier = cls.ACTIVITY_MULTIPLIERS.get(activity_level.lower(), 1.55)
        tdee = cls.calculate_tdee(bmr, activity_level)

        # Goal Adjustment based on desired rate
        # 1 kg fat ~= 7700 kcal -> 0.5 kg/week ~= 550 kcal/day adjustment
        rate = max(0.1, min(1.5, desired_rate))
        daily_kcal_delta = (rate * 7700.0) / 7.0

        if fitness_goal.lower() == "weight_loss":
            adj = -daily_kcal_delta
        elif fitness_goal.lower() == "weight_gain":
            adj = daily_kcal_delta
        elif fitness_goal.lower() == "muscle_building":
            adj = max(250.0, daily_kcal_delta * 0.5)
        else:
            adj = 0.0

        raw_target = tdee + adj

        # Enforce safe bounds
        safe_floor_applied = False
        if raw_target < settings.SAFE_MIN_CALORIES:
            target_calories = float(settings.SAFE_MIN_CALORIES)
            safe_floor_applied = True
        elif raw_target > settings.SAFE_MAX_CALORIES:
            target_calories = float(settings.SAFE_MAX_CALORIES)
        else:
            target_calories = round(raw_target, 2)

        # Macronutrient split rules
        # Protein: 1.6g to 2.2g per kg for fitness/muscle/weight loss; 1.2g for maintenance
        if fitness_goal.lower() in ["muscle_building", "weight_loss"]:
            protein_g_per_kg = 2.0
        else:
            protein_g_per_kg = 1.4

        protein_g = round(min(weight_kg * protein_g_per_kg, (target_calories * 0.35) / 4.0), 1)
        protein_kcal = protein_g * 4.0

        # Fat: 25-30% of total calories (or keto adjustment)
        if dietary_preference.lower() == "keto":
            fat_kcal = target_calories * 0.70
            fat_g = round(fat_kcal / 9.0, 1)
            carbs_kcal = max(0.0, target_calories - protein_kcal - fat_kcal)
            carbs_g = round(carbs_kcal / 4.0, 1)
        else:
            fat_kcal = target_calories * 0.28
            fat_g = round(fat_kcal / 9.0, 1)
            carbs_kcal = max(0.0, target_calories - protein_kcal - fat_kcal)
            carbs_g = round(carbs_kcal / 4.0, 1)

        # Fiber target: 14g per 1000 kcal (standard clinical guideline)
        fiber_g = round((target_calories / 1000.0) * 14.0, 1)

        # Hydration target: 35ml per kg body weight + exercise buffer
        water_ml = round(weight_kg * 35.0, 0)

        return {
            "bmr": bmr,
            "tdee": tdee,
            "target_calories": target_calories,
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
            "fiber_g": fiber_g,
            "water_ml": water_ml,
            "formula": "Mifflin-St Jeor",
            "activity_multiplier": multiplier,
            "calorie_adjustment": round(adj, 2),
            "safe_floor_applied": safe_floor_applied
        }

    # Configurable threshold deltas and ratios for calorie balance status
    STATUS_THRESHOLDS = {
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
            "upper_surplus": 250.0
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
        if percentage < (cls.STATUS_THRESHOLDS["very_low_ratio"] * 100.0):
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
        if percentage < (cls.STATUS_THRESHOLDS["below_target_ratio"] * 100.0):
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
            excess_margin = cls.STATUS_THRESHOLDS["weight_loss"]["upper_surplus"]
            goal_desc = "weight-loss"
        elif "maintain" in goal_lower:
            excess_margin = cls.STATUS_THRESHOLDS["maintenance"]["upper_surplus"]
            goal_desc = "maintenance"
        else:
            excess_margin = cls.STATUS_THRESHOLDS["weight_gain"]["upper_surplus"]
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
