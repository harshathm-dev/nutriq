from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class EntitlementOut(BaseModel):
    feature_key: str
    daily_quota: int
    is_enabled: int

    class Config:
        from_attributes = True

class SubscriptionOut(BaseModel):
    id: str
    user_id: str
    plan_tier: str
    billing_status: str
    current_period_end: Optional[datetime] = None
    entitlements: List[EntitlementOut] = []
    used_today_ai_calls: int = 0
    daily_limit: int = 15

    class Config:
        from_attributes = True

class PlanSubscribeRequest(BaseModel):
    plan_tier: str  # "free", "premium", "family"
