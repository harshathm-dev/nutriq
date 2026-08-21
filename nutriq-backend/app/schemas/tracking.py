from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator
from app.utils.date_utils import get_local_date, format_local_time

class ExerciseCreate(BaseModel):
    type: Optional[str] = None
    activity_type: Optional[str] = None
    activity_name: Optional[str] = None
    duration_min: Optional[int] = Field(None, ge=1, le=1440)
    duration_minutes: Optional[int] = Field(None, ge=1, le=1440)
    intensity: str = "moderate"  # "low", "moderate", "high"
    calories_burned_est: Optional[float] = None
    calories_burned: Optional[float] = None
    steps: Optional[int] = Field(0, ge=0)
    distance_km: Optional[float] = Field(0.0, ge=0.0)
    notes: Optional[str] = None
    recorded_at: Optional[datetime] = None
    date: Optional[str] = None
    time: Optional[str] = None

class ExerciseOut(BaseModel):
    id: str
    user_id: str
    type: str
    activity_type: str
    activity_name: str
    duration_min: int
    duration_minutes: int
    intensity: str = "moderate"
    calories_burned_est: float
    calories_burned: float
    steps: Optional[int] = 0
    distance_km: Optional[float] = 0.0
    notes: Optional[str] = None
    recorded_at: datetime
    activity_date: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    logged_at: Optional[str] = None

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def populate_exercise_fields(cls, data: Any) -> Any:
        rec = getattr(data, 'recorded_at', None) if not isinstance(data, dict) else data.get('recorded_at')
        act_type = getattr(data, 'type', None) if not isinstance(data, dict) else (data.get('type') or data.get('activity_type') or 'workout')
        dur = getattr(data, 'duration_min', None) if not isinstance(data, dict) else (data.get('duration_min') or data.get('duration_minutes') or 30)
        cal = getattr(data, 'calories_burned_est', None) if not isinstance(data, dict) else (data.get('calories_burned_est') or data.get('calories_burned') or 0.0)

        d_iso = get_local_date(rec).isoformat() if rec else ""
        t_str = format_local_time(rec) if rec else ""

        # Friendly name
        friendly_name = str(act_type).replace('_', ' ').title()

        if isinstance(data, dict):
            data.setdefault('activity_type', str(act_type))
            data.setdefault('activity_name', friendly_name)
            data.setdefault('duration_minutes', int(dur or 30))
            data.setdefault('duration_min', int(dur or 30))
            data.setdefault('calories_burned', float(cal or 0.0))
            data.setdefault('calories_burned_est', float(cal or 0.0))
            data.setdefault('activity_date', d_iso)
            data.setdefault('date', d_iso)
            data.setdefault('time', t_str)
            data.setdefault('logged_at', t_str)
        else:
            setattr(data, 'activity_type', str(act_type))
            setattr(data, 'activity_name', friendly_name)
            setattr(data, 'duration_minutes', int(dur or 30))
            setattr(data, 'calories_burned', float(cal or 0.0))
            setattr(data, 'activity_date', d_iso)
            setattr(data, 'date', d_iso)
            setattr(data, 'time', t_str)
            setattr(data, 'logged_at', t_str)
        return data

class DayActivityHistoryResponse(BaseModel):
    date: str
    display_date: str
    is_today: bool
    is_future: bool = False
    has_data: bool = False
    total_calories_burned: float = 0.0
    total_duration_minutes: int = 0
    total_steps: int = 0
    total_distance_km: float = 0.0
    activity_count: int = 0
    activities: List[ExerciseOut] = []

class WaterCreate(BaseModel):
    amount_ml: float = Field(..., ge=10, le=5000, description="Amount of water in ml (10ml to 5000ml)")
    recorded_at: Optional[datetime] = None
    date: Optional[str] = None
    time: Optional[str] = None

class WaterOut(BaseModel):
    id: str
    user_id: str
    amount_ml: float
    recorded_at: datetime
    date: Optional[str] = None
    time: Optional[str] = None

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def populate_date_time(cls, data: Any) -> Any:
        rec = getattr(data, 'recorded_at', None) if not isinstance(data, dict) else data.get('recorded_at')
        if rec:
            d_str = get_local_date(rec).isoformat()
            t_str = format_local_time(rec)
            if isinstance(data, dict):
                data.setdefault('date', d_str)
                data.setdefault('time', t_str)
            else:
                setattr(data, 'date', d_str)
                setattr(data, 'time', t_str)
        return data

class WaterTodaySummary(BaseModel):
    date: str
    consumed_ml: float
    target_ml: float
    remaining_ml: float
    completion_percentage: float
    logs: List[WaterOut] = []

class WeightCreate(BaseModel):
    weight_kg: float = Field(..., ge=20, le=400)
    recorded_at: Optional[datetime] = None

class WeightOut(BaseModel):
    id: str
    user_id: str
    weight_kg: float
    recorded_at: datetime

    class Config:
        from_attributes = True
