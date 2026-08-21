from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.user import User
from app.schemas.sync import SyncBatchRequest, SyncBatchResponse
from app.middleware.auth_middleware import get_current_user
from app.services.sync_service import SyncService

router = APIRouter(prefix="/sync", tags=["Offline Synchronization Engine"])

@router.post("", response_model=SyncBatchResponse)
async def process_sync(
    req: SyncBatchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    changes_dict = [c.model_dump() for c in req.changes]
    processed, conflicts, updates = await SyncService.process_sync_batch(
        session=session,
        user_id=current_user.id,
        device_id=req.device_id,
        changes=changes_dict
    )
    return SyncBatchResponse(
        status="success",
        processed_count=processed,
        conflicts_resolved=conflicts,
        server_sync_timestamp=datetime.now(timezone.utc),
        server_updates=updates
    )
