from typing import List, Optional
from pydantic import BaseModel, Field


class ReminderSettingsOut(BaseModel):
    reminders_enabled: bool = True
    breakfast_enabled: bool = True
    breakfast_time: str = "08:00"
    lunch_enabled: bool = True
    lunch_time: str = "13:00"
    snack_enabled: bool = True
    snack_time: str = "17:00"
    dinner_enabled: bool = True
    dinner_time: str = "20:00"
    grace_period_minutes: int = 30
    daily_summary_enabled: bool = True
    daily_summary_time: str = "20:30"
    user_timezone: str = "Asia/Kolkata"


class ReminderSettingsUpdate(BaseModel):
    reminders_enabled: Optional[bool] = None
    breakfast_enabled: Optional[bool] = None
    breakfast_time: Optional[str] = None
    lunch_enabled: Optional[bool] = None
    lunch_time: Optional[str] = None
    snack_enabled: Optional[bool] = None
    snack_time: Optional[str] = None
    dinner_enabled: Optional[bool] = None
    dinner_time: Optional[str] = None
    grace_period_minutes: Optional[int] = None
    daily_summary_enabled: Optional[bool] = None
    daily_summary_time: Optional[str] = None
    user_timezone: Optional[str] = None


class PendingReminderOut(BaseModel):
    has_pending: bool = False
    meal_type: Optional[str] = None  # "breakfast", "lunch", "snack", "dinner", "daily_summary"
    title: Optional[str] = None
    message: Optional[str] = None
    scheduled_time: Optional[str] = None
    remind_later_count: int = 0
    can_remind_later: bool = True
    action_url: Optional[str] = None
    date: Optional[str] = None


class ReminderActionRequest(BaseModel):
    meal_type: str
    action: str  # "log_meal", "remind_later", "dismiss"
    date: Optional[str] = None
