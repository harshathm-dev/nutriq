from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class ConsentRequest(BaseModel):
    consent_type: str  # "terms_of_service", "privacy_policy", "ai_health_processing"
    accepted: bool
    version: str = "2.0"

class ConsentOut(BaseModel):
    id: str
    consent_type: str
    version: str
    accepted_at: datetime
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DataExportOut(BaseModel):
    user_id: str
    generated_at: datetime
    profile: Optional[Dict[str, Any]]
    goals: List[Dict[str, Any]]
    meals: List[Dict[str, Any]]
    water_logs: List[Dict[str, Any]]
    exercise_logs: List[Dict[str, Any]]
    weight_logs: List[Dict[str, Any]]
    ai_recommendations: List[Dict[str, Any]]
    recipes: List[Dict[str, Any]]
    custom_foods: List[Dict[str, Any]]
