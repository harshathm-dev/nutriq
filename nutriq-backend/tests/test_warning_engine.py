import pytest
from app.services.warning_engine import WarningEngine

def test_excess_calorie_warning():
    warnings = WarningEngine.evaluate_warnings(
        consumed_calories=2400.0,
        target_calories=2000.0,
        consumed_protein_g=80.0,
        target_protein_g=100.0,
        fitness_goal="weight_loss"
    )
    warning_ids = [w["warning_id"] for w in warnings]
    assert "excess_calorie_warning" in warning_ids

def test_low_protein_warning():
    # Consumed 1500 kcal (>60% of 2000), but only 20g protein (<45% of 100g)
    warnings = WarningEngine.evaluate_warnings(
        consumed_calories=1500.0,
        target_calories=2000.0,
        consumed_protein_g=20.0,
        target_protein_g=100.0,
        fitness_goal="maintain"
    )
    warning_ids = [w["warning_id"] for w in warnings]
    assert "low_protein_warning" in warning_ids

def test_repeated_excess_trend():
    warnings = WarningEngine.evaluate_warnings(
        consumed_calories=2150.0,
        target_calories=2000.0,
        consumed_protein_g=95.0,
        target_protein_g=100.0,
        fitness_goal="weight_loss",
        recent_days_calorie_history=[2200.0, 2300.0, 2250.0, 2100.0]
    )
    warning_ids = [w["warning_id"] for w in warnings]
    assert "repeated_excess_warning" in warning_ids
