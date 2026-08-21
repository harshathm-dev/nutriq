from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class StreakDayStatus(BaseModel):
    date: str  # "YYYY-MM-DD"
    day_name: str  # "Mon", "Tue", etc.
    day_initial: str  # "M", "T", "W", "T", "F", "S", "S"
    completed: bool
    is_today: bool


class StreakStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_streak: int
    longest_streak: int
    total_active_days: int
    last_completed_date: Optional[str] = None
    completed_today: bool
    weekly_history: List[StreakDayStatus] = []
    new_milestone: Optional[int] = None
    milestones_achieved: List[int] = []


class StreakHistoryOut(BaseModel):
    current_streak: int
    longest_streak: int
    total_active_days: int
    last_completed_date: Optional[str] = None
    history: List[StreakDayStatus] = []


class MilestoneAckRequest(BaseModel):
    milestone: int
