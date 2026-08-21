from typing import List, Optional
from datetime import datetime, date
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.database.session import get_db
from app.models.user import User
from app.models.meal import Meal, MealItem
from app.schemas.meal import (
    MealCreate,
    MealUpdate,
    MealOut,
    MealTotals,
    DayMealHistoryResponse,
    MealHistoryRangeResponse
)
from app.middleware.auth_middleware import get_current_user
from app.services.meal_service import MealService

router = APIRouter(prefix="/meals", tags=["Meal Logging"])

@router.get("/today", response_model=List[MealOut])
async def get_today_meals(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieves ONLY meals logged today in the user's timezone (Asia/Kolkata default),
    sorted in ascending chronological order (oldest to newest).
    """
    meals = await MealService.get_today_meals(session, current_user.id)
    out = []
    for m in meals:
        totals = MealService.compute_totals(m.items)
        out.append(MealOut(
            id=m.id,
            user_id=m.user_id,
            meal_type=m.meal_type,
            occurred_at=m.occurred_at,
            source=m.source,
            sync_version=m.sync_version,
            items=m.items,
            totals=totals,
            created_at=m.created_at,
            updated_at=m.updated_at
        ))
    return out

@router.get("/history/range", response_model=MealHistoryRangeResponse)
async def get_meal_history_range(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieves meal counts and nutrition summaries for a calendar range.
    """
    try:
        start_d = date.fromisoformat(start_date.split("T")[0])
        end_d = date.fromisoformat(end_date.split("T")[0])
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD.")

    if start_d > end_d:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date must be before or equal to end_date.")

    data = await MealService.get_meals_history_range(session, current_user.id, start_d, end_d)
    return data

@router.get("/history", response_model=DayMealHistoryResponse)
async def get_day_meal_history(
    date_str: Optional[str] = Query(None, alias="date", description="Target date (YYYY-MM-DD). Defaults to today."),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieves full day-wise meal history and nutrition breakdown for the given date.
    """
    if date_str:
        try:
            target_d = date.fromisoformat(date_str.split("T")[0])
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        tz = ZoneInfo("Asia/Kolkata")
        target_d = datetime.now(tz).date()

    history_data = await MealService.get_meals_by_date(session, current_user.id, target_d)
    return history_data

@router.get("", response_model=List[MealOut])
async def list_meals(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    meals = await MealService.get_user_meals(session, current_user.id, start_date, end_date)
    out = []
    for m in meals:
        totals = MealService.compute_totals(m.items)
        out.append(MealOut(
            id=m.id,
            user_id=m.user_id,
            meal_type=m.meal_type,
            occurred_at=m.occurred_at,
            source=m.source,
            sync_version=m.sync_version,
            items=m.items,
            totals=totals,
            created_at=m.created_at,
            updated_at=m.updated_at
        ))
    return out

@router.post("", response_model=MealOut, status_code=status.HTTP_201_CREATED)
async def create_meal(
    req: MealCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    meal = await MealService.create_meal(session, current_user.id, req)
    totals = MealService.compute_totals(meal.items)

    return MealOut(
        id=meal.id,
        user_id=meal.user_id,
        meal_type=meal.meal_type,
        occurred_at=meal.occurred_at,
        source=meal.source,
        sync_version=meal.sync_version,
        items=meal.items,
        totals=totals,
        created_at=meal.created_at,
        updated_at=meal.updated_at
    )

@router.get("/{meal_id}", response_model=MealOut)
async def get_meal(
    meal_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(Meal).where(
        and_(Meal.id == meal_id, Meal.user_id == current_user.id)
    ).options(selectinload(Meal.items))
    res = await session.execute(stmt)
    meal = res.scalar_one_or_none()
    if not meal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
    totals = MealService.compute_totals(meal.items)
    return MealOut(
        id=meal.id,
        user_id=meal.user_id,
        meal_type=meal.meal_type,
        occurred_at=meal.occurred_at,
        source=meal.source,
        sync_version=meal.sync_version,
        items=meal.items,
        totals=totals,
        created_at=meal.created_at,
        updated_at=meal.updated_at
    )

@router.put("/{meal_id}", response_model=MealOut)
async def update_meal(
    meal_id: str,
    req: MealUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    updated = await MealService.update_meal(session, current_user.id, meal_id, req)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
    totals = MealService.compute_totals(updated.items)
    return MealOut(
        id=updated.id,
        user_id=updated.user_id,
        meal_type=updated.meal_type,
        occurred_at=updated.occurred_at,
        source=updated.source,
        sync_version=updated.sync_version,
        items=updated.items,
        totals=totals,
        created_at=updated.created_at,
        updated_at=updated.updated_at
    )

@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal(
    meal_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    success = await MealService.delete_meal(session, current_user.id, meal_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
    return None

