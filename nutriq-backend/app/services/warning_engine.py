from typing import List, Dict, Any
from datetime import datetime, timezone

class WarningEngine:
    """
    Deterministic Contextual Smart Warning Engine
    Zero LLM hallucination - evaluated through explicit clinical/behavioral rules.
    """

    @classmethod
    def evaluate_warnings(
        cls,
        consumed_calories: float,
        target_calories: float,
        consumed_protein_g: float,
        target_protein_g: float,
        fitness_goal: str,
        recent_days_calorie_history: List[float] = None
    ) -> List[Dict[str, Any]]:
        warnings = []
        recent_days = recent_days_calorie_history or []

        # 1. Excess-Calorie Warning (Contextual: only when exceeding target by >10% for weight loss/maintenance)
        calorie_surplus = consumed_calories - target_calories
        if calorie_surplus > (target_calories * 0.10) and fitness_goal in ["weight_loss", "maintain"]:
            warnings.append({
                "warning_id": "excess_calorie_warning",
                "type": "calorie_excess",
                "severity": "high" if calorie_surplus > (target_calories * 0.25) else "medium",
                "message": f"You have exceeded your daily calorie target by {int(calorie_surplus)} kcal. Consider a lighter dinner or an evening walk.",
                "evidence": {
                    "consumed_calories": consumed_calories,
                    "target_calories": target_calories,
                    "surplus": calorie_surplus,
                    "percentage_over": round((calorie_surplus / target_calories) * 100, 1)
                }
            })

        # 2. Low-Protein Warning (If consumed >60% of daily calories but protein is <45% of target)
        if consumed_calories >= (target_calories * 0.60) and consumed_protein_g < (target_protein_g * 0.45):
            protein_gap = round(target_protein_g - consumed_protein_g, 1)
            warnings.append({
                "warning_id": "low_protein_warning",
                "type": "macro_imbalance",
                "severity": "medium",
                "message": f"Protein intake is lagging ({consumed_protein_g}g / {target_protein_g}g). Try adding paneer, eggs, sprouts, or Greek yogurt to your next meal.",
                "evidence": {
                    "consumed_protein_g": consumed_protein_g,
                    "target_protein_g": target_protein_g,
                    "protein_gap_g": protein_gap
                }
            })

        # 3. Repeated-Excess Trend Warning (If 3 or more recent days exceeded target)
        if len(recent_days) >= 3:
            exceeded_count = sum(1 for cal in recent_days[-5:] if cal > target_calories * 1.05)
            if exceeded_count >= 3:
                warnings.append({
                    "warning_id": "repeated_excess_warning",
                    "type": "trend",
                    "severity": "high",
                    "message": f"You have exceeded your calorie target on {exceeded_count} of your last recorded days. Would you like to adjust your target or review high-calorie snacks?",
                    "evidence": {
                        "days_exceeded": exceeded_count,
                        "history_sample": recent_days[-5:]
                    }
                })

        return warnings
