from typing import Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_db
from app.models.user import User
from app.models.profile import UserProfile
from app.models.goal import Goal
from app.models.tracking import WeightHistory
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileOut
from app.middleware.auth_middleware import get_current_user

logger = logging.getLogger("nutriq.profile")
router = APIRouter(prefix="/profile", tags=["Profile"])

@router.get("", response_model=Optional[ProfileOut])
async def get_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

@router.post("", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile(
    req: ProfileCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            for key, val in req.model_dump(exclude_unset=True).items():
                if val is not None:
                    setattr(existing, key, val)
            profile = existing
        else:
            profile = UserProfile(
                user_id=current_user.id,
                **req.model_dump()
            )
            session.add(profile)

        # Sync/Create active Goal if fitness goal and weight are provided
        if profile.fitness_goal and profile.weight_kg:
            goal_stmt = select(Goal).where(Goal.user_id == current_user.id, Goal.active == True)
            goal_res = await session.execute(goal_stmt)
            active_goal = goal_res.scalars().first()
            if not active_goal:
                weight_val = float(profile.weight_kg)
                target_wt = weight_val * 0.9 if profile.fitness_goal == "weight_loss" else (weight_val * 1.05 if profile.fitness_goal == "weight_gain" else weight_val)
                new_goal = Goal(
                    user_id=current_user.id,
                    goal_type=profile.fitness_goal,
                    current_weight_kg=weight_val,
                    target_weight_kg=target_wt,
                    desired_rate=0.5,
                    active=True
                )
                session.add(new_goal)
            else:
                active_goal.goal_type = profile.fitness_goal

        # Add initial weight history entry if none exists
        if profile.weight_kg:
            wt_stmt = select(WeightHistory).where(WeightHistory.user_id == current_user.id)
            wt_res = await session.execute(wt_stmt)
            if not wt_res.scalars().first():
                session.add(WeightHistory(user_id=current_user.id, weight_kg=float(profile.weight_kg)))

        await session.commit()
        await session.refresh(profile)
        return profile
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to create/save profile for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize profile. Please try again."
        )

@router.put("", response_model=ProfileOut)
async def update_profile(
    req: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
        result = await session.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            profile = UserProfile(user_id=current_user.id, **req.model_dump(exclude_unset=True))
            session.add(profile)
        else:
            for key, val in req.model_dump(exclude_unset=True).items():
                if val is not None:
                    setattr(profile, key, val)

        # Sync/Create active Goal if fitness goal and weight are provided
        if profile.fitness_goal and profile.weight_kg:
            goal_stmt = select(Goal).where(Goal.user_id == current_user.id, Goal.active == True)
            goal_res = await session.execute(goal_stmt)
            active_goal = goal_res.scalars().first()
            if not active_goal:
                weight_val = float(profile.weight_kg)
                target_wt = weight_val * 0.9 if profile.fitness_goal == "weight_loss" else (weight_val * 1.05 if profile.fitness_goal == "weight_gain" else weight_val)
                new_goal = Goal(
                    user_id=current_user.id,
                    goal_type=profile.fitness_goal,
                    current_weight_kg=weight_val,
                    target_weight_kg=target_wt,
                    desired_rate=0.5,
                    active=True
                )
                session.add(new_goal)
            else:
                active_goal.goal_type = profile.fitness_goal

        await session.commit()
        await session.refresh(profile)
        return profile
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to update profile for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile. Please try again."
        )
