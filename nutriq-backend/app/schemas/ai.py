from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from app.schemas.meal import MealItemCreate

class ExtractedFoodItem(BaseModel):
    food_name: str
    quantity: float = 1.0
    serving_unit: str = "serving"
    estimated_grams: float = 100.0
    matched_food_id: Optional[str] = None
    calories: float
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    sugar_g: float = 0.0
    sodium_mg: float = 0.0
    confidence: float = 1.0
    needs_confirmation: bool = False

class NaturalLanguageFoodRequest(BaseModel):
    text: str
    meal_type: Optional[str] = "breakfast"

class NaturalLanguageFoodResponse(BaseModel):
    raw_query: str
    inferred_meal_type: str
    items: List[ExtractedFoodItem]
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    confidence_score: float
    confirmation_required: bool

class FoodImageAnalysisRequest(BaseModel):
    image_base64: Optional[str] = None
    image_url: Optional[str] = None
    meal_type: Optional[str] = "lunch"

class FoodImageAnalysisResponse(BaseModel):
    detected_dishes: List[ExtractedFoodItem]
    portion_confidence: float
    nutrition_estimate: Dict[str, float]
    disclaimer: str = "Portion and nutritional estimates are AI-derived and require user confirmation."

class AIRecommendationOut(BaseModel):
    id: str
    user_id: str
    recommendation_type: str
    title: str
    content: str
    metadata_json: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class AIWarningOut(BaseModel):
    id: str
    user_id: str
    warning_id: str
    type: str
    severity: str
    message: str
    evidence: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AIChatMessage(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str

class AIChatRequest(BaseModel):
    messages: List[AIChatMessage]
    include_today_context: bool = True

class AIChatResponse(BaseModel):
    response: str
    answer: Optional[str] = None
    recommendations: List[Dict[str, Any]] = []
    warnings: List[str] = []
    remaining_calories: Optional[float] = None
    remaining_protein: Optional[float] = None
    sources: List[str] = ["NutriQ Verified Food Database", "IFCT"]
    suggested_actions: List[str] = []
    disclaimer: str = "NutriQ AI provides nutrition estimates and education, not clinical diagnoses or medical advice."

class MealPlanDay(BaseModel):
    day: str
    target_calories: float
    meals: Dict[str, Any]

class MealPlanRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=14)
    budget_level: str = "medium"  # "budget", "medium", "premium"
    dietary_notes: Optional[str] = ""
    mode: Optional[str] = "generate"  # "generate" or "regenerate"
    previous_plan_id: Optional[str] = None
    exclude_food_ids: Optional[List[str]] = None
    regeneration_id: Optional[str] = None

class MealPlanOut(BaseModel):
    id: str
    user_id: str
    title: str
    plan_payload: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class AIHabitAnalysisResponse(BaseModel):
    summary: str
    key_patterns: List[str]
    macro_adherence: str
    recommendations: List[str]
    consistency_score: int  # 0 to 100
