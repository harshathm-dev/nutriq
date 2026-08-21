from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.user import User
from app.middleware.auth_middleware import get_current_user
from app.services.daily_summary_service import DailySummaryService
from app.schemas.daily_summary import DailySummaryResponse

router = APIRouter(prefix="/daily-summary", tags=["Daily Nutrition Summary"])


@router.get("", response_model=DailySummaryResponse)
async def get_daily_summary(
    date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieves the complete daily nutrition overview for the authenticated user for the given date (default today).
    Never fabricates calories, macros, hydration, or meals.
    """
    summary = await DailySummaryService.get_daily_summary(
        session=session,
        user_id=current_user.id,
        target_date_str=date
    )
    return summary
