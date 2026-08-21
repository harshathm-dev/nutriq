from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.user import User
from app.middleware.auth_middleware import get_current_user
from app.services.nutrition_warning_service import NutritionWarningService
from app.services.food_recommendation_service import FoodRecommendationService
from app.schemas.nutrition_status import NutritionStatusResponse, FoodRecommendationItem

router = APIRouter(prefix="/nutrition", tags=["Smart Nutrition Status & Warnings"])

@router.get("/status", response_model=NutritionStatusResponse)
async def get_nutrition_status(
    date: Optional[str] = Query(None, description="ISO date string (YYYY-MM-DD)"),
    meal_type: Optional[str] = Query(None, description="Current or upcoming meal slot (breakfast, lunch, snack, dinner)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Evaluates real-time nutrition status, caloric deficit/surplus, goal warnings,
    and returns personalized food recommendations directly from the active NutriQ database.
    """
    status_data = await NutritionWarningService.evaluate_status(
        session=session,
        user_id=current_user.id,
        target_date_str=date
    )

    recommendations = await FoodRecommendationService.get_recommendations(
        session=session,
        user_id=current_user.id,
        nutrition_status=status_data,
        meal_type=meal_type,
        limit=4
    )

    return {
        **status_data,
        "recommendations": recommendations
    }

@router.get("/recommendations", response_model=List[FoodRecommendationItem])
async def get_food_recommendations(
    meal_type: Optional[str] = Query(None, description="Meal slot (breakfast, lunch, snack, dinner)"),
    date: Optional[str] = Query(None, description="Target date (YYYY-MM-DD)"),
    limit: int = Query(4, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Returns personalized portion-specific food recommendations strictly from the database.
    """
    status_data = await NutritionWarningService.evaluate_status(
        session=session,
        user_id=current_user.id,
        target_date_str=date
    )

    return await FoodRecommendationService.get_recommendations(
        session=session,
        user_id=current_user.id,
        nutrition_status=status_data,
        meal_type=meal_type,
        limit=limit
    )
