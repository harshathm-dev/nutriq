from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class FoodRecommendationItem(BaseModel):
    food_id: str
    food_name: str
    category: str
    serving_quantity: float
    serving_unit: str
    grams: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    meal_type: str
    reason: str
    suitability_score: Optional[float] = None
    model_version: Optional[str] = None
    recommendation_source: Optional[str] = "ml_model"
    dietary_tags: List[str] = []

class NutritionWarningDetail(BaseModel):
    warning_id: str
    level: str  # "on_track", "near_target", "slightly_above", "significantly_above", "below_target", "very_low", "target_exceeded", "no_meals"
    title: str
    message: str
    why_it_matters: Optional[str] = None
    action_tip: Optional[str] = None

class NutritionStatusResponse(BaseModel):
    date: str
    goal: str
    goal_display: str
    daily_calorie_target: float
    calories_consumed: float
    calories_burned: float = 0.0
    calories_remaining: float
    calorie_difference: float
    net_energy_after_exercise: float = 0.0
    status_level: str  # "on_track", "below_target", "very_low", "target_exceeded", "no_meals", "slightly_above", "significantly_above"
    status_badge: str
    calorie_status: Optional[Dict[str, Any]] = None
    warning_title: Optional[str] = None
    warning_message: Optional[str] = None
    why_it_matters: Optional[str] = None
    positive_feedback: Optional[str] = None
    protein_status: Optional[str] = None
    protein_warning: Optional[str] = None
    weekly_pattern_warning: Optional[str] = None
    has_meals_logged: bool
    macros: Dict[str, Any]
    recommendations: List[FoodRecommendationItem] = []
