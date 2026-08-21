from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_db
from app.models.user import User
from app.models.profile import UserProfile
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileOut
from app.middleware.auth_middleware import get_current_user

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
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        for key, val in req.model_dump(exclude_unset=True).items():
            if val is not None:
                setattr(existing, key, val)
        await session.commit()
        await session.refresh(existing)
        return existing

    profile = UserProfile(
        user_id=current_user.id,
        **req.model_dump()
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile

@router.put("", response_model=ProfileOut)
async def update_profile(
    req: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
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

    await session.commit()
    await session.refresh(profile)
    return profile
