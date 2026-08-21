from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.user import User
from app.middleware.auth_middleware import get_current_user
from app.services.food_recommendation_service import FoodRecommendationService
from app.schemas.recommendations import RecommendationRequest, RecommendationResponse, FoodRecommendationItem

router = APIRouter(prefix="/recommendations", tags=["Smart Nutrition Recommendations"])


@router.post("", response_model=RecommendationResponse)
async def get_smart_recommendations_post(
    req: RecommendationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    POST /api/recommendations
    Analyzes today's actual food intake, profile, and remaining requirements to produce
    ML-ranked, goal-aligned, calorie-safe food recommendations with clear nutritional rationale.
    """
    res = await FoodRecommendationService.get_smart_recommendations(
        session=session,
        user_id=current_user.id,
        target_date_str=req.date,
        meal_type=req.meal_type,
        limit=req.limit
    )
    return res


@router.get("", response_model=RecommendationResponse)
async def get_smart_recommendations_get(
    date: Optional[str] = Query(None, description="Target date (YYYY-MM-DD)"),
    meal_type: Optional[str] = Query(None, description="Meal slot (breakfast, lunch, snack, dinner)"),
    limit: int = Query(4, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    GET /api/recommendations
    Returns personalized smart food recommendations for the specified date and meal context.
    """
    res = await FoodRecommendationService.get_smart_recommendations(
        session=session,
        user_id=current_user.id,
        target_date_str=date,
        meal_type=meal_type,
        limit=limit
    )
    return res
