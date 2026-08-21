from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    date: Optional[str] = Field(None, description="ISO date string (YYYY-MM-DD)")
    meal_type: Optional[str] = Field(None, description="Meal slot (breakfast, lunch, snack, dinner)")
    limit: int = Field(4, ge=1, le=10, description="Max recommendations to return")


class FoodRecommendationItem(BaseModel):
    food_id: str
    food_name: str
    category: str = "General"
    serving_quantity: float = 1.0
    serving_unit: str = "serving"
    grams: float = 100.0
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float = 0.0
    # Aliases
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    meal_type: str = "snack"
    suitability_score: float = 0.8
    score: Optional[float] = None
    model_version: str = "1.0.0"
    recommendation_source: str = "ml_model"
    reason: str
    dietary_tags: List[str] = []


class RemainingNeeds(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    water_l: float


class NutritionGaps(BaseModel):
    protein: str = "MODERATE"
    calories: str = "MODERATE"
    fiber: str = "MODERATE"
    fat: str = "MODERATE"
    hydration: str = "NEAR TARGET"


class RecommendationResponse(BaseModel):
    recommendations: List[FoodRecommendationItem]
    remaining_needs: RemainingNeeds
    gaps: NutritionGaps
    goal: str = "weight_loss"
    goal_display: str = "Weight Loss"
    target_meal_type: str = "snack"
    is_empty_day: bool = False
    is_future: bool = False
    message: Optional[str] = None
