from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class GoalBase(BaseModel):
    goal_type: str = Field(..., description="'weight_loss', 'maintain', 'weight_gain', 'muscle_building'")
    current_weight_kg: float = Field(..., ge=20, le=400)
    target_weight_kg: float = Field(..., ge=20, le=400)
    desired_rate: float = Field(default=0.5, ge=0.1, le=1.5, description="kg/week")
    target_date: Optional[datetime] = None

class GoalCreate(GoalBase):
    pass

class GoalUpdate(BaseModel):
    goal_type: Optional[str] = None
    current_weight_kg: Optional[float] = None
    target_weight_kg: Optional[float] = None
    desired_rate: Optional[float] = None
    target_date: Optional[datetime] = None
    active: Optional[bool] = None

class GoalOut(GoalBase):
    id: str
    user_id: str
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class NutritionTargetsOut(BaseModel):
    bmr: float
    tdee: float
    target_calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    water_ml: float
    formula: str = "Mifflin-St Jeor"
    activity_multiplier: float
    calorie_adjustment: float
    safe_floor_applied: bool = False


class GoalProgressOut(BaseModel):
    goal_type: str
    starting_weight_kg: float
    current_weight_kg: float
    target_weight_kg: float
    weight_lost_kg: float
    weight_remaining_kg: float
    progress_percentage: float
    weekly_pace_kg: float
    recommended_weekly_pace_kg: float
    estimated_target_date: Optional[str] = None
    estimated_weeks_remaining: float
    calorie_target: float
    tdee: float
    bmr: float
    is_pace_aggressive: bool = False
    pace_warning_message: Optional[str] = None
    is_deficit_excessive: bool = False
    deficit_warning_message: Optional[str] = None
    has_active_goal: bool = True
