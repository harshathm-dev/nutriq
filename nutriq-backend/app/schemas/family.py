from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class AllergyCreate(BaseModel):
    allergen_type: str  # "Dairy / Lactose", "Gluten", "Peanuts", "Tree Nuts", "Shellfish", "Soy", "Eggs"
    severity: str = "moderate"
    notes: Optional[str] = ""
    family_profile_id: Optional[str] = None

class AllergyOut(AllergyCreate):
    id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True
