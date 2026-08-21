from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, date as dt_date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database.session import get_db
from app.models.user import User
from app.models.profile import UserProfile
from app.models.goal import Goal
from app.models.tracking import Exercise, Water, WeightHistory
from app.schemas.tracking import (
    ExerciseCreate, ExerciseOut, DayActivityHistoryResponse,
    WaterCreate, WaterOut, WaterTodaySummary,
    WeightCreate, WeightOut
)
from app.middleware.auth_middleware import get_current_user
from app.utils.date_utils import (
    get_date_bounds_utc,
    parse_datetime_with_tz,
    get_today_local,
    get_local_date,
    DEFAULT_TIMEZONE
)

router = APIRouter(tags=["Tracking (Activities/Exercise, Water, Weight)"])

# Centralized MET Configuration for Physical Activity
MET_CONFIG = {
    "walking": {"low": 2.8, "moderate": 3.5, "high": 4.5},
    "running": {"low": 7.0, "moderate": 9.8, "high": 12.0},
    "jogging": {"low": 6.0, "moderate": 7.5, "high": 9.0},
    "cycling": {"low": 5.5, "moderate": 7.5, "high": 10.0},
    "gym_workout": {"low": 4.0, "moderate": 6.0, "high": 8.0},
    "gym": {"low": 4.0, "moderate": 6.0, "high": 8.0},
    "weight_training": {"low": 3.8, "moderate": 5.5, "high": 7.5},
    "strength": {"low": 4.0, "moderate": 6.0, "high": 8.0},
    "strength_training": {"low": 4.0, "moderate": 6.0, "high": 8.0},
    "swimming": {"low": 5.0, "moderate": 7.0, "high": 9.5},
    "yoga": {"low": 2.5, "moderate": 3.2, "high": 4.0},
    "sports": {"low": 5.0, "moderate": 7.0, "high": 9.0},
    "household": {"low": 2.0, "moderate": 3.0, "high": 4.0},
    "household_activity": {"low": 2.0, "moderate": 3.0, "high": 4.0},
    "cardio": {"low": 5.5, "moderate": 7.5, "high": 10.0},
    "other": {"low": 3.0, "moderate": 4.5, "high": 6.0}
}

def estimate_exercise_calories(
    activity_type: str,
    duration_min: int,
    intensity: str = "moderate",
    weight_kg: float = 70.0
) -> float:
    """
    Deterministic MET Calculation:
    Calories burned = MET * 3.5 * weight_kg / 200 * duration_minutes
    """
    act_key = (activity_type or "other").lower().strip().replace(" ", "_").replace("/", "_").replace("-", "_")
    matched = None
    for k, v in MET_CONFIG.items():
        if k in act_key or act_key in k:
            matched = v
            break
    if not matched:
        matched = MET_CONFIG["other"]

    intensity_key = (intensity or "moderate").lower().strip()
    met = matched.get(intensity_key, matched.get("moderate", 4.5))
    burned = (met * 3.5 * weight_kg / 200.0) * duration_min
    return round(burned, 1)


# =============================================================================
# EXERCISE & ACTIVITIES ENDPOINTS
# =============================================================================

@router.get("/activity/today", response_model=List[ExerciseOut])
@router.get("/activities/today", response_model=List[ExerciseOut])
@router.get("/exercise/today", response_model=List[ExerciseOut])
async def get_today_activities(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieves ONLY physical activities logged today in the user's timezone (Asia/Kolkata default),
    sorted in ascending chronological order.
    """
    today_local = get_today_local()
    start_utc, end_utc = get_date_bounds_utc(today_local)

    stmt = select(Exercise).where(
        and_(
            Exercise.user_id == current_user.id,
            Exercise.recorded_at >= start_utc,
            Exercise.recorded_at < end_utc
        )
    ).order_by(Exercise.recorded_at.asc())

    res = await session.execute(stmt)
    return list(res.scalars().all())


@router.get("/activity/history", response_model=DayActivityHistoryResponse)
@router.get("/activities/history", response_model=DayActivityHistoryResponse)
@router.get("/exercise/history", response_model=DayActivityHistoryResponse)
async def get_activity_history(
    date_str: Optional[str] = Query(None, alias="date", description="Target date (YYYY-MM-DD). Defaults to today."),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieves full day-wise physical activity history and aggregated metrics (calories, duration, steps)
    for the given date strictly filtered by the authenticated user.
    """
    if date_str:
        try:
            target_d = dt_date.fromisoformat(date_str.split("T")[0])
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        target_d = get_today_local()

    today_local = get_today_local()
    is_today = (target_d == today_local)
    is_future = (target_d > today_local)
    display_date_str = target_d.strftime("%A, %B %d, %Y")

    start_utc, end_utc = get_date_bounds_utc(target_d)

    stmt = select(Exercise).where(
        and_(
            Exercise.user_id == current_user.id,
            Exercise.recorded_at >= start_utc,
            Exercise.recorded_at < end_utc
        )
    ).order_by(Exercise.recorded_at.asc())

    res = await session.execute(stmt)
    activities = list(res.scalars().all())

    total_cal = sum(float(a.calories_burned_est or 0.0) for a in activities)
    total_dur = sum(int(a.duration_min or 0) for a in activities)
    total_steps = sum(int(a.steps or 0) for a in activities)
    total_dist = sum(float(a.distance_km or 0.0) for a in activities)

    return DayActivityHistoryResponse(
        date=target_d.isoformat(),
        display_date=display_date_str,
        is_today=is_today,
        is_future=is_future,
        has_data=len(activities) > 0,
        total_calories_burned=round(total_cal, 1),
        total_duration_minutes=total_dur,
        total_steps=total_steps,
        total_distance_km=round(total_dist, 2),
        activity_count=len(activities),
        activities=activities
    )


@router.get("/activities", response_model=List[ExerciseOut])
@router.get("/exercise", response_model=List[ExerciseOut])
async def list_activities(
    date: Optional[str] = Query(None, description="Optional YYYY-MM-DD filter"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(Exercise).where(Exercise.user_id == current_user.id)
    if date:
        try:
            target_d = dt_date.fromisoformat(date.split("T")[0])
            start_utc, end_utc = get_date_bounds_utc(target_d)
            stmt = stmt.where(and_(Exercise.recorded_at >= start_utc, Exercise.recorded_at < end_utc))
        except ValueError:
            pass

    stmt = stmt.order_by(Exercise.recorded_at.desc())
    res = await session.execute(stmt)
    return list(res.scalars().all())


@router.post("/activities", response_model=ExerciseOut, status_code=status.HTTP_201_CREATED)
@router.post("/exercise", response_model=ExerciseOut, status_code=status.HTTP_201_CREATED)
async def create_activity(
    req: ExerciseCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    act_type = req.activity_type or req.type or "walking"
    duration = req.duration_minutes or req.duration_min or 30
    if duration <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duration must be greater than 0 minutes.")

    intensity = req.intensity or "moderate"

    # Get user profile weight for accurate MET calculation
    prof_stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    prof_res = await session.execute(prof_stmt)
    prof = prof_res.scalar_one_or_none()
    weight_kg = float(prof.weight_kg) if prof and prof.weight_kg else 70.0

    # Custom calories burned or MET estimation
    custom_burned = req.calories_burned if req.calories_burned is not None else req.calories_burned_est
    if custom_burned is not None and custom_burned > 0:
        burned = round(float(custom_burned), 1)
    else:
        burned = estimate_exercise_calories(act_type, duration, intensity, weight_kg)

    recorded_dt = parse_datetime_with_tz(
        date_str=req.date,
        time_str=req.time,
        fallback_dt=req.recorded_at
    )

    ex = Exercise(
        user_id=current_user.id,
        type=act_type,
        duration_min=duration,
        intensity=intensity,
        calories_burned_est=burned,
        steps=int(req.steps or 0),
        distance_km=float(req.distance_km or 0.0),
        notes=req.notes or "",
        recorded_at=recorded_dt
    )
    session.add(ex)
    await session.commit()
    await session.refresh(ex)

    try:
        from app.services.streak_service import StreakService
        await StreakService.record_activity(session, current_user.id)
    except Exception:
        pass

    return ex


@router.put("/activities/{activity_id}", response_model=ExerciseOut)
@router.put("/exercise/{activity_id}", response_model=ExerciseOut)
async def update_activity(
    activity_id: str,
    req: ExerciseCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(Exercise).where(and_(Exercise.id == activity_id, Exercise.user_id == current_user.id))
    res = await session.execute(stmt)
    ex = res.scalar_one_or_none()
    if not ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity record not found")

    act_type = req.activity_type or req.type or ex.type
    duration = req.duration_minutes or req.duration_min or ex.duration_min
    if duration <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duration must be greater than 0 minutes.")
    intensity = req.intensity or ex.intensity or "moderate"

    prof_stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    prof_res = await session.execute(prof_stmt)
    prof = prof_res.scalar_one_or_none()
    weight_kg = float(prof.weight_kg) if prof and prof.weight_kg else 70.0

    custom_burned = req.calories_burned if req.calories_burned is not None else req.calories_burned_est
    if custom_burned is not None and custom_burned > 0:
        burned = round(float(custom_burned), 1)
    else:
        burned = estimate_exercise_calories(act_type, duration, intensity, weight_kg)

    ex.type = act_type
    ex.duration_min = duration
    ex.intensity = intensity
    ex.calories_burned_est = burned
    if req.steps is not None:
        ex.steps = int(req.steps)
    if req.distance_km is not None:
        ex.distance_km = float(req.distance_km)
    if req.notes is not None:
        ex.notes = req.notes

    if req.date or req.time or req.recorded_at:
        ex.recorded_at = parse_datetime_with_tz(
            date_str=req.date,
            time_str=req.time,
            fallback_dt=req.recorded_at or ex.recorded_at
        )

    await session.commit()
    await session.refresh(ex)
    return ex


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/exercise/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity(
    activity_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(Exercise).where(and_(Exercise.id == activity_id, Exercise.user_id == current_user.id))
    res = await session.execute(stmt)
    ex = res.scalar_one_or_none()
    if not ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity record not found")
    await session.delete(ex)
    await session.commit()
    return None


# =============================================================================
# WATER TRACKING ENDPOINTS
# =============================================================================

@router.get("/water", response_model=List[WaterOut])
async def list_water(
    date: Optional[str] = Query(None, description="Optional YYYY-MM-DD filter"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(Water).where(Water.user_id == current_user.id)
    if date:
        try:
            target_d = dt_date.fromisoformat(date.split("T")[0])
            start_utc, end_utc = get_date_bounds_utc(target_d)
            stmt = stmt.where(and_(Water.recorded_at >= start_utc, Water.recorded_at < end_utc))
        except ValueError:
            pass

    stmt = stmt.order_by(Water.recorded_at.desc())
    res = await session.execute(stmt)
    return list(res.scalars().all())


@router.get("/water/today", response_model=WaterTodaySummary)
async def get_today_water_summary(
    date: Optional[str] = Query(None, description="Optional YYYY-MM-DD (defaults to local today)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    if date:
        try:
            target_d = dt_date.fromisoformat(date.split("T")[0])
        except ValueError:
            target_d = get_today_local()
    else:
        target_d = get_today_local()

    start_utc, end_utc = get_date_bounds_utc(target_d)

    prof_res = await session.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = prof_res.scalar_one_or_none()
    weight_kg = profile.weight_kg if profile else 70.0
    water_target = round(weight_kg * 35.0, 0) if weight_kg else 2500.0

    stmt = select(Water).where(
        and_(
            Water.user_id == current_user.id,
            Water.recorded_at >= start_utc,
            Water.recorded_at < end_utc
        )
    ).order_by(Water.recorded_at.desc())

    res = await session.execute(stmt)
    logs = list(res.scalars().all())
    consumed = sum(float(w.amount_ml or 0.0) for w in logs)
    remaining = max(0.0, water_target - consumed)
    pct = round((consumed / water_target) * 100.0, 1) if water_target > 0 else 0.0

    return WaterTodaySummary(
        date=target_d.isoformat(),
        consumed_ml=round(consumed, 1),
        target_ml=round(water_target, 1),
        remaining_ml=round(remaining, 1),
        completion_percentage=pct,
        logs=logs
    )


@router.post("/water", response_model=WaterOut, status_code=status.HTTP_201_CREATED)
async def create_water(
    req: WaterCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    recorded_dt = parse_datetime_with_tz(
        date_str=req.date,
        time_str=req.time,
        fallback_dt=req.recorded_at
    )

    w = Water(
        user_id=current_user.id,
        amount_ml=req.amount_ml,
        recorded_at=recorded_dt
    )
    session.add(w)
    await session.commit()
    await session.refresh(w)

    try:
        from app.services.streak_service import StreakService
        await StreakService.record_activity(session, current_user.id)
    except Exception:
        pass

    return w


@router.delete("/water/{water_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_water(
    water_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(Water).where(and_(Water.id == water_id, Water.user_id == current_user.id))
    res = await session.execute(stmt)
    w = res.scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Water record not found")
    await session.delete(w)
    await session.commit()
    return None


# =============================================================================
# WEIGHT TRACKING ENDPOINTS
# =============================================================================

@router.get("/weight", response_model=List[WeightOut])
async def list_weights(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(WeightHistory).where(WeightHistory.user_id == current_user.id).order_by(WeightHistory.recorded_at.desc())
    res = await session.execute(stmt)
    return list(res.scalars().all())


@router.post("/weight", response_model=WeightOut, status_code=status.HTTP_201_CREATED)
async def create_weight(
    req: WeightCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    recorded_dt = req.recorded_at or datetime.now(timezone.utc)

    # 1. Update user profile weight
    prof_stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    prof_res = await session.execute(prof_stmt)
    prof = prof_res.scalar_one_or_none()
    if prof:
        prof.weight_kg = req.weight_kg

    # 2. Insert into weight history
    wh = WeightHistory(
        user_id=current_user.id,
        weight_kg=req.weight_kg,
        recorded_at=recorded_dt
    )
    session.add(wh)
    await session.commit()
    await session.refresh(wh)

    return wh
