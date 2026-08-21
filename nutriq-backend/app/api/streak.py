from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.user import User
from app.schemas.streak import StreakStatusOut, StreakHistoryOut, MilestoneAckRequest
from app.middleware.auth_middleware import get_current_user
from app.services.streak_service import StreakService

router = APIRouter(prefix="/streak", tags=["NutriQ Daily Streak"])


@router.get("", response_model=StreakStatusOut)
@router.get("/status", response_model=StreakStatusOut)
async def get_streak_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Returns the user's daily streak status, weekly progress, and milestones.
    """
    status = await StreakService.calculate_streak_status(session, current_user.id)
    return status


@router.post("/check", response_model=StreakStatusOut)
async def check_streak_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Forces an evaluation / recalculation of the user's streak status.
    """
    status = await StreakService.calculate_streak_status(session, current_user.id)
    return status


@router.get("/history", response_model=StreakHistoryOut)
async def get_streak_history(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Returns streak tracking history and weekly completion data.
    """
    status = await StreakService.calculate_streak_status(session, current_user.id)
    return {
        "current_streak": status["current_streak"],
        "longest_streak": status["longest_streak"],
        "total_active_days": status["total_active_days"],
        "last_completed_date": status["last_completed_date"],
        "history": status["weekly_history"]
    }


@router.post("/milestone-ack")
async def acknowledge_milestone(
    req: MilestoneAckRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Acknowledges a milestone celebration so it is not displayed repeatedly.
    """
    acked = await StreakService.acknowledge_milestone(session, current_user.id, req.milestone)
    return {"success": True, "milestone": req.milestone, "acknowledged": acked}
