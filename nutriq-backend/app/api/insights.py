from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

from app.database.session import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.services.nutrition_warning_service import NutritionWarningService

router = APIRouter(prefix="/nutrition", tags=["Nutrition Insights"])


@router.get("/insights", response_model=Dict[str, Any])
async def get_nutrition_insights(
    date: Optional[str] = Query(None, description="Target date in YYYY-MM-DD format"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Returns dynamic, un-fabricated nutrition insights for the authenticated user on a specific date.
    All insights are calculated strictly from the user's recorded meals, water, activity, and goals.
    """
    return await NutritionWarningService.generate_nutrition_insights(
        session=session,
        user_id=current_user.id,
        target_date_str=date
    )
