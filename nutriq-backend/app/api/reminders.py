from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.user import User
from app.middleware.auth_middleware import get_current_user
from app.services.reminder_service import ReminderService
from app.schemas.reminder import (
    ReminderSettingsOut,
    ReminderSettingsUpdate,
    PendingReminderOut,
    ReminderActionRequest
)

router = APIRouter(prefix="/reminders", tags=["Smart Meal Reminders"])


@router.get("/settings", response_model=ReminderSettingsOut)
async def get_reminder_settings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    setting = await ReminderService.get_or_create_settings(session, current_user.id)
    return setting


@router.put("/settings", response_model=ReminderSettingsOut)
async def update_reminder_settings(
    req: ReminderSettingsUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    updates = req.model_dump(exclude_unset=True)
    setting = await ReminderService.update_settings(session, current_user.id, updates)
    return setting


@router.get("/pending", response_model=PendingReminderOut)
async def check_pending_reminders(
    current_time: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Checks if any meal reminder is currently due based on the user's scheduled times,
    grace period, and real-time journal.
    """
    pending = await ReminderService.get_pending_reminders(
        session=session,
        user_id=current_user.id,
        current_time_iso=current_time
    )
    return pending


@router.post("/respond")
async def respond_to_reminder(
    req: ReminderActionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Responds to a reminder:
    - log_meal: marks reminder completed
    - remind_later: delays 30 mins (max 2 times)
    - dismiss: stops reminder for today
    """
    result = await ReminderService.handle_reminder_action(
        session=session,
        user_id=current_user.id,
        meal_type=req.meal_type,
        action=req.action,
        target_date_str=req.date
    )
    return result
