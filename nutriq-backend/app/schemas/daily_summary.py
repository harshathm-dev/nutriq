from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class CalorieSummary(BaseModel):
    target: float
    consumed: float
    remaining: float
    burned: float = 0.0
    net: float = 0.0
    is_over: bool = False
    over_amount: float = 0.0


class MacroItem(BaseModel):
    target: float
    consumed: float
    percentage: float = 0.0


class MacroSummary(BaseModel):
    protein: MacroItem
    carbohydrates: MacroItem
    fat: MacroItem
    fiber: Optional[MacroItem] = None


class HydrationSummary(BaseModel):
    target_ml: float
    consumed_ml: float
    remaining_ml: float
    percentage: float
    is_zero: bool = False


class MealItemDetail(BaseModel):
    food_name: str
    quantity: float
    serving_unit: str
    grams: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float = 0.0


class MealSlotStatus(BaseModel):
    logged: bool
    status_label: str  # "Logged" or "Not logged"
    meal_count: int = 0
    total_calories: float = 0.0
    total_protein_g: float = 0.0
    total_carbs_g: float = 0.0
    total_fat_g: float = 0.0
    total_fiber_g: float = 0.0
    items: List[MealItemDetail] = []


class MealsStatusSummary(BaseModel):
    breakfast: MealSlotStatus
    lunch: MealSlotStatus
    snack: MealSlotStatus
    dinner: MealSlotStatus
    logged_count: int = 0
    total_slots: int = 4


class ExerciseItemDetail(BaseModel):
    id: str
    type: str
    activity_name: str
    duration_min: int
    intensity: str = "moderate"
    calories_burned: float
    time: str = ""
    recorded_at: str

class ExerciseSummary(BaseModel):
    logged: bool
    duration_minutes: int = 0
    calories_burned: float = 0.0
    activities: List[str] = []
    items: List[ExerciseItemDetail] = []
    message: str = "No exercise logged today."


class DailySummaryResponse(BaseModel):
    date: str  # "YYYY-MM-DD"
    display_date: str  # e.g. "August 19, 2026"
    is_today: bool = True
    is_future: bool = False
    has_data: bool = False
    calories: CalorieSummary
    macros: MacroSummary
    hydration: HydrationSummary
    meals: MealsStatusSummary
    exercise: ExerciseSummary
    goal: str = "weight_loss"
    goal_display: str = "Weight Loss"
    goal_status: str = "Within today's target"
    daily_insight: str = "Keep logging your meals and hydration to see daily insights."
    calorie_warning: Optional[str] = None
    progress_score: Optional[int] = None
    progress_score_explanation: Optional[str] = None
    empty_state_message: Optional[str] = None
