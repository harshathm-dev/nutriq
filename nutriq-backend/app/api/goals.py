from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.database.session import get_db
from app.models.user import User
from app.models.goal import Goal
from app.models.profile import UserProfile
from app.models.tracking import WeightHistory
from app.schemas.goal import GoalCreate, GoalUpdate, GoalOut, NutritionTargetsOut, GoalProgressOut
from app.middleware.auth_middleware import get_current_user
from app.services.nutrition_engine import NutritionEngine

router = APIRouter(prefix="/goals", tags=["Goals"])


@router.get("/progress", response_model=GoalProgressOut)
async def get_goal_progress(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Computes dynamic goal progress, weight projection, safe weekly pace,
    and estimated completion date.
    """
    # 1. Fetch profile
    prof_stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    prof_res = await session.execute(prof_stmt)
    profile = prof_res.scalar_one_or_none()

    current_weight = float(profile.weight_kg if profile and profile.weight_kg else 70.0)

    # 2. Fetch active goal
    g_stmt = select(Goal).where(Goal.user_id == current_user.id, Goal.active == True).order_by(Goal.created_at.desc())
    g_res = await session.execute(g_stmt)
    goal = g_res.scalars().first()

    # 3. Fetch latest weight history
    wt_stmt = select(WeightHistory).where(WeightHistory.user_id == current_user.id).order_by(WeightHistory.recorded_at.desc())
    wt_res = await session.execute(wt_stmt)
    latest_wt = wt_res.scalars().first()
    if latest_wt and latest_wt.weight_kg:
        current_weight = float(latest_wt.weight_kg)

    if not goal:
        goal_type = profile.fitness_goal if profile and profile.fitness_goal else "maintain"
        target_weight = current_weight
        start_weight = current_weight
        desired_rate = 0.5
        has_active_goal = False
    else:
        goal_type = goal.goal_type
        target_weight = float(goal.target_weight_kg)
        start_weight = float(goal.current_weight_kg)
        desired_rate = float(goal.desired_rate or 0.5)
        has_active_goal = True

    age = int(profile.age if profile and profile.age else 25)
    gender = str(profile.gender if profile and profile.gender else "other")
    height_cm = float(profile.height_cm if profile and profile.height_cm else 170.0)
    activity_level = str(profile.activity_level if profile and profile.activity_level else "moderately_active")
    dietary_pref = str(profile.dietary_preference if profile and profile.dietary_preference else "standard")

    targets = NutritionEngine.calculate_targets(
        weight_kg=current_weight,
        height_cm=height_cm,
        age=age,
        gender=gender,
        activity_level=activity_level,
        fitness_goal=goal_type,
        desired_rate=desired_rate,
        dietary_preference=dietary_pref
    )
    tdee = float(targets["tdee"])
    bmr = float(targets["bmr"])
    calorie_target = float(targets["target_calories"])

    # Distance and progress calculations
    weight_remaining = round(abs(current_weight - target_weight), 1)

    if goal_type in ["weight_loss"]:
        weight_lost = max(0.0, round(start_weight - current_weight, 1))
        total_delta = max(0.1, abs(start_weight - target_weight))
        progress_pct = min(100.0, max(0.0, round((weight_lost / total_delta) * 100.0, 1)))
    elif goal_type in ["weight_gain", "muscle_building"]:
        weight_gained = max(0.0, round(current_weight - start_weight, 1))
        total_delta = max(0.1, abs(target_weight - start_weight))
        progress_pct = min(100.0, max(0.0, round((weight_gained / total_delta) * 100.0, 1)))
    else:
        # Maintain
        weight_lost = 0.0
        progress_pct = 100.0 if abs(current_weight - target_weight) <= 1.0 else 90.0

    # Estimated time and target date
    if weight_remaining <= 0.2:
        est_weeks = 0.0
        est_target_date = "Goal Achieved! 🎉"
    else:
        safe_pace = max(0.1, desired_rate)
        est_weeks = round(weight_remaining / safe_pace, 1)
        est_date = datetime.now(timezone.utc) + timedelta(weeks=est_weeks)
        est_target_date = est_date.strftime("%B %Y")

    # Safe pace and deficit warnings
    is_pace_aggressive = desired_rate > 1.0
    pace_warning = None
    if is_pace_aggressive:
        pace_warning = (
            f"Your selected pace of {desired_rate} kg/week may be too aggressive. "
            "A slower pace (0.5–0.75 kg/week) is more sustainable."
        )

    is_deficit_excessive = (tdee - calorie_target) > 1000 or calorie_target < 1200
    deficit_warning = None
    if is_deficit_excessive:
        deficit_warning = "Your current calorie target may create a large calorie deficit. Consider a more sustainable target."

    return GoalProgressOut(
        goal_type=goal_type,
        starting_weight_kg=start_weight,
        current_weight_kg=current_weight,
        target_weight_kg=target_weight,
        weight_lost_kg=weight_lost if goal_type in ["weight_loss"] else 0.0,
        weight_remaining_kg=weight_remaining,
        progress_percentage=progress_pct,
        weekly_pace_kg=desired_rate,
        recommended_weekly_pace_kg=0.5,
        estimated_target_date=est_target_date,
        estimated_weeks_remaining=est_weeks,
        calorie_target=calorie_target,
        tdee=tdee,
        bmr=bmr,
        is_pace_aggressive=is_pace_aggressive,
        pace_warning_message=pace_warning,
        is_deficit_excessive=is_deficit_excessive,
        deficit_warning_message=deficit_warning,
        has_active_goal=has_active_goal
    )


@router.get("", response_model=List[GoalOut])
async def get_goals(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(Goal).where(Goal.user_id == current_user.id).order_by(Goal.created_at.desc())
    res = await session.execute(stmt)
    return list(res.scalars().all())


@router.post("", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def create_goal(
    req: GoalCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    # Deactivate existing active goals
    await session.execute(
        update(Goal).where(Goal.user_id == current_user.id).values(active=False)
    )
    goal = Goal(
        user_id=current_user.id,
        goal_type=req.goal_type,
        current_weight_kg=req.current_weight_kg,
        target_weight_kg=req.target_weight_kg,
        desired_rate=req.desired_rate,
        target_date=req.target_date,
        active=True
    )
    session.add(goal)

    # Sync profile weight if current weight is given
    prof_stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    prof_res = await session.execute(prof_stmt)
    prof = prof_res.scalar_one_or_none()
    if prof:
        prof.fitness_goal = req.goal_type
        prof.weight_kg = req.current_weight_kg

    await session.commit()
    await session.refresh(goal)
    return goal


@router.put("/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: str,
    req: GoalUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id)
    res = await session.execute(stmt)
    goal = res.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    for k, v in req.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(goal, k, v)

    # Sync profile
    if req.current_weight_kg or req.goal_type:
        prof_stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
        prof_res = await session.execute(prof_stmt)
        prof = prof_res.scalar_one_or_none()
        if prof:
            if req.current_weight_kg:
                prof.weight_kg = req.current_weight_kg
            if req.goal_type:
                prof.fitness_goal = req.goal_type

    await session.commit()
    await session.refresh(goal)
    return goal

