from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator
from app.utils.date_utils import get_local_date, format_local_time

class MealItemCreate(BaseModel):
    food_id: Optional[str] = None
    food_name: Optional[str] = None
    name: Optional[str] = None
    quantity: float = Field(default=1.0, ge=0.01)
    portion: Optional[float] = None
    serving_unit: str = "serving"
    grams: float = Field(default=100.0, ge=0.1)
    calories: float
    protein_g: float = 0.0
    protein: Optional[float] = None
    carbs_g: float = 0.0
    carbs: Optional[float] = None
    fat_g: float = 0.0
    fat: Optional[float] = None
    fiber_g: float = 0.0
    fiber: Optional[float] = None
    sugar_g: float = 0.0
    sodium_mg: float = 0.0

    @model_validator(mode='before')
    @classmethod
    def resolve_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # food_name <-> name
            if not data.get('food_name') and data.get('name'):
                data['food_name'] = str(data['name'])
            elif not data.get('name') and data.get('food_name'):
                data['name'] = str(data['food_name'])
            # quantity <-> portion
            if data.get('portion') is not None and data.get('quantity') is None:
                data['quantity'] = float(data['portion'])
            elif data.get('quantity') is not None and data.get('portion') is None:
                data['portion'] = float(data['quantity'])
            # protein
            if data.get('protein') is not None and data.get('protein_g') is None:
                data['protein_g'] = float(data['protein'])
            elif data.get('protein_g') is not None and data.get('protein') is None:
                data['protein'] = float(data['protein_g'])
            # carbs
            if data.get('carbs') is not None and data.get('carbs_g') is None:
                data['carbs_g'] = float(data['carbs'])
            elif data.get('carbs_g') is not None and data.get('carbs') is None:
                data['carbs'] = float(data['carbs_g'])
            # fat
            if data.get('fat') is not None and data.get('fat_g') is None:
                data['fat_g'] = float(data['fat'])
            elif data.get('fat_g') is not None and data.get('fat') is None:
                data['fat'] = float(data['fat_g'])
            # fiber
            if data.get('fiber') is not None and data.get('fiber_g') is None:
                data['fiber_g'] = float(data['fiber'])
            elif data.get('fiber_g') is not None and data.get('fiber') is None:
                data['fiber'] = float(data['fiber_g'])
        return data

class MealItemOut(MealItemCreate):
    id: str
    meal_id: str
    food_name: str
    name: str
    portion: float
    protein: float
    carbs: float
    fat: float
    fiber: float

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def populate_item_out_fields(cls, data: Any) -> Any:
        fname = getattr(data, 'food_name', None) if not isinstance(data, dict) else data.get('food_name')
        name_val = getattr(data, 'name', None) if not isinstance(data, dict) else data.get('name')
        actual_name = fname or name_val or 'Food item'

        qty = getattr(data, 'quantity', None) if not isinstance(data, dict) else data.get('quantity')
        portion_val = getattr(data, 'portion', None) if not isinstance(data, dict) else data.get('portion')
        actual_qty = float(qty if qty is not None else (portion_val if portion_val is not None else 1.0))

        pro = getattr(data, 'protein_g', None) if not isinstance(data, dict) else data.get('protein_g')
        actual_pro = float(pro if pro is not None else 0.0)

        carb = getattr(data, 'carbs_g', None) if not isinstance(data, dict) else data.get('carbs_g')
        actual_carb = float(carb if carb is not None else 0.0)

        fat_val = getattr(data, 'fat_g', None) if not isinstance(data, dict) else data.get('fat_g')
        actual_fat = float(fat_val if fat_val is not None else 0.0)

        fib = getattr(data, 'fiber_g', None) if not isinstance(data, dict) else data.get('fiber_g')
        actual_fib = float(fib if fib is not None else 0.0)

        if isinstance(data, dict):
            data['food_name'] = actual_name
            data['name'] = actual_name
            data['quantity'] = actual_qty
            data['portion'] = actual_qty
            data['protein_g'] = actual_pro
            data['protein'] = actual_pro
            data['carbs_g'] = actual_carb
            data['carbs'] = actual_carb
            data['fat_g'] = actual_fat
            data['fat'] = actual_fat
            data['fiber_g'] = actual_fib
            data['fiber'] = actual_fib
        else:
            setattr(data, 'name', actual_name)
            setattr(data, 'food_name', actual_name)
            setattr(data, 'portion', actual_qty)
            setattr(data, 'protein', actual_pro)
            setattr(data, 'carbs', actual_carb)
            setattr(data, 'fat', actual_fat)
            setattr(data, 'fiber', actual_fib)
        return data

class MealCreate(BaseModel):
    meal_type: str = Field(..., description="'breakfast', 'mid_morning_snack', 'lunch', 'evening_snack', 'dinner', 'other'")
    occurred_at: Optional[datetime] = None
    date: Optional[str] = None
    time: Optional[str] = None
    source: str = "manual"
    items: List[MealItemCreate]

class MealUpdate(BaseModel):
    meal_type: Optional[str] = None
    occurred_at: Optional[datetime] = None
    date: Optional[str] = None
    time: Optional[str] = None
    items: Optional[List[MealItemCreate]] = None

class MealTotals(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    sugar_g: float
    sodium_mg: float

class MealOut(BaseModel):
    id: str
    user_id: str
    meal_type: str
    name: Optional[str] = None
    occurred_at: datetime
    meal_date: Optional[str] = None
    logged_time: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    meal_time: Optional[str] = None
    source: str = "manual"
    sync_version: int = 1
    items: List[MealItemOut]
    totals: MealTotals
    total_calories: Optional[float] = None
    calories: Optional[float] = None
    total_protein: Optional[float] = None
    protein: Optional[float] = None
    total_carbs: Optional[float] = None
    carbs: Optional[float] = None
    total_fat: Optional[float] = None
    fat: Optional[float] = None
    total_fiber: Optional[float] = None
    fiber: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def populate_date_and_total_fields(cls, data: Any) -> Any:
        occ = getattr(data, 'occurred_at', None) if not isinstance(data, dict) else data.get('occurred_at')
        if occ:
            d_iso = get_local_date(occ).isoformat()
            t_str = format_local_time(occ)
            m_type = getattr(data, 'meal_type', 'breakfast') if not isinstance(data, dict) else data.get('meal_type', 'breakfast')
            display_name = m_type.replace('_', ' ').title() if m_type else 'Meal'

            totals_obj = getattr(data, 'totals', None) if not isinstance(data, dict) else data.get('totals')
            t_cal = getattr(totals_obj, 'calories', 0.0) if hasattr(totals_obj, 'calories') else (totals_obj.get('calories', 0.0) if isinstance(totals_obj, dict) else 0.0)
            t_pro = getattr(totals_obj, 'protein_g', 0.0) if hasattr(totals_obj, 'protein_g') else (totals_obj.get('protein_g', 0.0) if isinstance(totals_obj, dict) else 0.0)
            t_carb = getattr(totals_obj, 'carbs_g', 0.0) if hasattr(totals_obj, 'carbs_g') else (totals_obj.get('carbs_g', 0.0) if isinstance(totals_obj, dict) else 0.0)
            t_fat = getattr(totals_obj, 'fat_g', 0.0) if hasattr(totals_obj, 'fat_g') else (totals_obj.get('fat_g', 0.0) if isinstance(totals_obj, dict) else 0.0)
            t_fib = getattr(totals_obj, 'fiber_g', 0.0) if hasattr(totals_obj, 'fiber_g') else (totals_obj.get('fiber_g', 0.0) if isinstance(totals_obj, dict) else 0.0)

            if isinstance(data, dict):
                data.setdefault('name', display_name)
                data.setdefault('meal_date', d_iso)
                data.setdefault('date', d_iso)
                data.setdefault('logged_time', t_str)
                data.setdefault('time', t_str)
                data.setdefault('meal_time', t_str)
                data.setdefault('total_calories', t_cal)
                data.setdefault('calories', t_cal)
                data.setdefault('total_protein', t_pro)
                data.setdefault('protein', t_pro)
                data.setdefault('total_carbs', t_carb)
                data.setdefault('carbs', t_carb)
                data.setdefault('total_fat', t_fat)
                data.setdefault('fat', t_fat)
                data.setdefault('total_fiber', t_fib)
                data.setdefault('fiber', t_fib)
            else:
                setattr(data, 'name', display_name)
                setattr(data, 'meal_date', d_iso)
                setattr(data, 'date', d_iso)
                setattr(data, 'logged_time', t_str)
                setattr(data, 'time', t_str)
                setattr(data, 'meal_time', t_str)
                setattr(data, 'total_calories', t_cal)
                setattr(data, 'calories', t_cal)
                setattr(data, 'total_protein', t_pro)
                setattr(data, 'protein', t_pro)
                setattr(data, 'total_carbs', t_carb)
                setattr(data, 'carbs', t_carb)
                setattr(data, 'total_fat', t_fat)
                setattr(data, 'fat', t_fat)
                setattr(data, 'total_fiber', t_fib)
                setattr(data, 'fiber', t_fib)
        return data

class DayMealHistoryResponse(BaseModel):
    date: str
    display_date: str
    is_today: bool
    is_future: bool = False
    has_data: bool = False
    total_calories: float = 0.0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fat: float = 0.0
    total_fiber: float = 0.0
    target_calories: float = 2000.0
    target_protein: float = 100.0
    target_carbs: float = 250.0
    target_fat: float = 60.0
    target_fiber: float = 28.0
    water_ml: float = 0.0
    water_target_ml: float = 2500.0
    exercise_calories: float = 0.0
    meal_count: int = 0
    meals: List[MealOut] = []

class MealHistoryRangeDay(BaseModel):
    date: str
    display_date: str
    total_calories: float = 0.0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fat: float = 0.0
    meal_count: int = 0
    is_today: bool = False

class MealHistoryRangeResponse(BaseModel):
    start_date: str
    end_date: str
    days: List[MealHistoryRangeDay]
    total_meals: int

class FavoriteMealCreate(BaseModel):
    name: str
    meal_type: str = "breakfast"
    items: List[MealItemCreate]

class FavoriteMealOut(BaseModel):
    id: str
    name: str
    meal_type: str
    template_payload: str
    created_at: datetime

    class Config:
        from_attributes = True

class RecipeIngredientCreate(BaseModel):
    food_id: Optional[str] = None
    food_name: str
    quantity: float
    unit: str
    grams: float

class RecipeIngredientOut(RecipeIngredientCreate):
    id: str
    recipe_id: str

    class Config:
        from_attributes = True

class RecipeCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    servings: int = 1
    ingredients: List[RecipeIngredientCreate]

class RecipeOut(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    servings: int
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    ingredients: List[RecipeIngredientOut]
    created_at: datetime

    class Config:
        from_attributes = True
