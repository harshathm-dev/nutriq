from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from app.database.session import get_db
from app.models.user import User
from app.models.family import Allergy
from app.schemas.family import AllergyCreate, AllergyOut
from app.middleware.auth_middleware import get_current_user

router = APIRouter(tags=["Allergies"])

@router.get("/allergies", response_model=List[AllergyOut])
async def list_allergies(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(Allergy).where(Allergy.user_id == current_user.id)
    res = await session.execute(stmt)
    return list(res.scalars().all())

@router.post("/allergies", response_model=AllergyOut, status_code=status.HTTP_201_CREATED)
async def add_allergy(
    req: AllergyCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    allergy = Allergy(
        user_id=current_user.id,
        family_profile_id=req.family_profile_id,
        allergen_type=req.allergen_type,
        severity=req.severity,
        notes=req.notes or ""
    )
    session.add(allergy)
    await session.commit()
    await session.refresh(allergy)
    return allergy

@router.delete("/allergies/{allergy_id}")
async def delete_allergy(
    allergy_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(Allergy).where(and_(Allergy.id == allergy_id, Allergy.user_id == current_user.id))
    res = await session.execute(stmt)
    allergy = res.scalar_one_or_none()
    if not allergy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allergy not found")

    await session.delete(allergy)
    await session.commit()
    return {"status": "success", "message": "Allergy deleted"}
