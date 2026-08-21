from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ProfileBase(BaseModel):
    name: str
    age: int = Field(..., ge=10, le=120)
    gender: str = Field(..., description="'male', 'female', or 'other'")
    height_cm: float = Field(..., ge=50, le=280)
    weight_kg: float = Field(..., ge=20, le=400)
    activity_level: str = Field(
        default="moderately_active",
        description="'sedentary', 'lightly_active', 'moderately_active', 'very_active', 'extremely_active'"
    )
    fitness_goal: str = Field(
        default="maintain",
        description="'weight_loss', 'maintain', 'weight_gain', 'muscle_building'"
    )
    dietary_preference: str = Field(
        default="standard",
        description="'standard', 'vegetarian', 'vegan', 'keto', 'pescatarian', 'jain', 'eggetarian'"
    )
    food_preferences: Optional[str] = ""

class ProfileCreate(ProfileBase):
    pass

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity_level: Optional[str] = None
    fitness_goal: Optional[str] = None
    dietary_preference: Optional[str] = None
    food_preferences: Optional[str] = None

class ProfileOut(ProfileBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
