from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.user import User
from app.schemas.privacy import ConsentRequest, ConsentOut, DataExportOut
from app.middleware.auth_middleware import get_current_user
from app.services.privacy_service import PrivacyService

router = APIRouter(prefix="/privacy", tags=["Privacy, Consent & Data Governance"])

@router.post("/consent", response_model=ConsentOut)
async def submit_consent(
    req: ConsentRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    rec = await PrivacyService.record_consent(session, current_user.id, req.consent_type, req.version)
    return rec

@router.get("/consent", response_model=list[ConsentOut])
@router.get("/consents", response_model=list[ConsentOut])
async def get_consents(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    recs = await PrivacyService.get_user_consents(session, current_user.id)
    return recs

@router.get("/export", response_model=DataExportOut)
async def export_data(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    data = await PrivacyService.export_all_user_data(session, current_user.id)
    return data

@router.delete("/account")
async def delete_account(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    success = await PrivacyService.delete_user_account_cascade(session, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"status": "success", "message": "User account and all personal health data permanently deleted."}
