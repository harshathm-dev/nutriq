from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class DailySummaryBrief(BaseModel):
    day_name: str
    date: str
    calories_consumed: float
    calorie_target: float
    exercise_burned_kcal: float = 0.0
    active_minutes: int = 0
    activities: List[str] = []
    protein_consumed_g: float
    protein_target_g: float
    carbs_consumed_g: float
    fat_consumed_g: float
    fiber_consumed_g: float
    water_consumed_ml: float
    water_target_ml: float
    meals_logged_count: int
    is_complete: bool
    breakfast_logged: bool
    lunch_logged: bool
    snack_logged: bool
    dinner_logged: bool
    is_today: bool = False
    is_future: bool = False
    has_data: bool = False
    # Convenient aliases
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    water_ml: Optional[float] = None

class WeeklyTotalsAndAverages(BaseModel):
    total_weekly_calories: float
    avg_daily_calories: float
    calorie_target: float
    total_protein_g: float
    avg_protein_g: float
    protein_target_g: float
    total_carbs_g: float
    avg_carbs_g: float
    total_fat_g: float
    avg_fat_g: float
    total_fiber_g: float
    avg_fiber_g: float
    total_water_ml: float
    avg_water_ml: float
    water_target_ml: float
    total_calories_burned: float = 0.0
    avg_daily_calories_burned: float = 0.0
    total_active_minutes: int = 0
    active_days: str = "0/7"
    active_days_count: int = 0
    total_meals_logged: int
    days_with_complete_logging: int
    days_with_missed_meals: int
    goal_adherence_pct: float
    elapsed_days: int = 7
    avg_label: str = "7-Day Average"

class WeeklySummaryResponse(BaseModel):
    week_start: str
    week_end: str
    display_range: str
    has_data: bool
    summary: WeeklyTotalsAndAverages
    daily_breakdown: List[DailySummaryBrief]
    insights: List[str]
    empty_state_message: Optional[str] = None
