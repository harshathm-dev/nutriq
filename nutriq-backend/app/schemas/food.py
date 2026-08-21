from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class ServingConversionOut(BaseModel):
    id: str
    serving_label: str
    grams: float
    unit: str

    class Config:
        from_attributes = True

class FoodBase(BaseModel):
    name: str
    category: str
    code: Optional[str] = None
    subcategory: Optional[str] = None
    region: Optional[str] = None
    serving_size_desc: Optional[str] = None
    serving_size: float = 100.0
    unit: str = "g"
    calories: float
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    sugar_g: float = 0.0
    sodium_mg: float = 0.0
    calcium_mg: Optional[float] = None
    iron_mg: Optional[float] = None
    vitamin_c_mg: Optional[float] = None
    folate_ug: Optional[float] = None
    source: str = "IFCT"
    barcode: Optional[str] = None
    normalized_key: Optional[str] = None

class FoodCreate(FoodBase):
    pass

class FoodOut(FoodBase):
    id: str
    updated_at: datetime
    serving_conversions: List[ServingConversionOut] = []
    is_favorite: Optional[bool] = False

    class Config:
        from_attributes = True


class CustomFoodCreate(BaseModel):
    name: str
    category: str = "Custom"
    serving_size: float = 100.0
    unit: str = "g"
    calories: float
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    sugar_g: float = 0.0
    sodium_mg: float = 0.0
    is_private: bool = True

class CustomFoodOut(CustomFoodCreate):
    id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True
