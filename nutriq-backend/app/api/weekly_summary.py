from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.user import User
from app.middleware.auth_middleware import get_current_user
from app.services.weekly_summary_service import WeeklySummaryService
from app.schemas.weekly_summary import WeeklySummaryResponse

router = APIRouter(tags=["Weekly Nutrition Summary"])

@router.get("/weekly-summary", response_model=WeeklySummaryResponse)
@router.get("/summary/weekly", response_model=WeeklySummaryResponse)
async def get_weekly_summary(
    week_start: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieves the 7-day weekly nutrition summary, daily breakdowns, and rule-based insights for the authenticated user.
    """
    return await WeeklySummaryService.get_weekly_summary(
        session=session,
        user_id=current_user.id,
        week_start_str=week_start
    )
