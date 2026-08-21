from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class AnalyticsSummary(BaseModel):
    avg_calories: float = 0.0
    prev_avg_calories: Optional[float] = None
    calorie_change_pct: Optional[float] = None
    target_calories: float = 2000.0
    avg_protein: float = 0.0
    target_protein: float = 100.0
    avg_water_liters: float = 0.0
    target_water_liters: float = 2.5
    goal_adherence_pct: float = 0.0
    total_tracked_days: int = 0
    total_period_days: int = 7
    has_data: bool = False

class DailyCalorieData(BaseModel):
    date: str
    display_date: str
    consumed: float
    target: float
    diff: float
    status: str  # "under", "target", "over", "unlogged"
    is_tracked: bool

class DailyHydrationData(BaseModel):
    date: str
    display_date: str
    consumed_liters: float
    consumed_ml: float
    target_liters: float
    target_ml: float
    goal_achieved: bool
    is_tracked: bool

class HydrationSummary(BaseModel):
    avg_liters: float = 0.0
    target_liters: float = 2.5
    best_day: Optional[Dict[str, Any]] = None
    days_goal_achieved: int = 0
    total_days: int = 7
    insight: str = ""

class DailyMacroData(BaseModel):
    date: str
    display_date: str
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    calories: float = 0.0
    protein_pct: float = 0.0
    carbs_pct: float = 0.0
    fat_pct: float = 0.0
    is_tracked: bool = False

class MacroAverages(BaseModel):
    avg_protein_g: float = 0.0
    avg_carbs_g: float = 0.0
    avg_fat_g: float = 0.0
    avg_fiber_g: float = 0.0
    protein_calories_pct: float = 0.0
    carbs_calories_pct: float = 0.0
    fat_calories_pct: float = 0.0

class DailyProteinData(BaseModel):
    date: str
    display_date: str
    consumed_g: float = 0.0
    target_g: float = 100.0
    achieved_pct: float = 0.0
    is_tracked: bool = False

class ProteinSummary(BaseModel):
    avg_protein: float = 0.0
    target_protein: float = 100.0
    achievement_pct: float = 0.0
    days_met: int = 0
    total_days: int = 7

class DailyActivityData(BaseModel):
    date: str
    display_date: str
    calories_burned: float = 0.0
    duration_minutes: int = 0
    steps: int = 0
    distance_km: float = 0.0
    has_activity: bool = False

class ActivitySummary(BaseModel):
    total_calories_burned: float = 0.0
    total_duration_minutes: int = 0
    avg_calories_burned: float = 0.0
    total_steps: int = 0
    most_active_day: Optional[Dict[str, Any]] = None

class DailyCalorieBalanceData(BaseModel):
    date: str
    display_date: str
    intake: float = 0.0
    burned: float = 0.0
    net: float = 0.0
    target: float = 2000.0
    is_tracked: bool = False

class WeightDataPoint(BaseModel):
    date: str
    display_date: str
    weight_kg: float
    recorded_at: Optional[str] = None

class WeightProgressSummary(BaseModel):
    current_weight_kg: Optional[float] = None
    target_weight_kg: Optional[float] = None
    starting_weight_kg: Optional[float] = None
    weight_change_kg: Optional[float] = None
    has_history: bool = False
    history: List[WeightDataPoint] = []

class AnalyticsRangeResponse(BaseModel):
    range: str
    start_date: str
    end_date: str
    summary: AnalyticsSummary
    calories: List[DailyCalorieData] = []
    calorie_insight: str = ""
    hydration: List[DailyHydrationData] = []
    hydration_summary: HydrationSummary
    macros: List[DailyMacroData] = []
    macro_averages: MacroAverages
    protein: List[DailyProteinData] = []
    protein_summary: ProteinSummary
    activity: List[DailyActivityData] = []
    activity_summary: ActivitySummary
    calorie_balance: List[DailyCalorieBalanceData] = []
    weight_progress: WeightProgressSummary
    nutrition_insights: List[str] = []
