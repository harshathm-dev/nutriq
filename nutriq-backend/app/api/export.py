import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.user import User
from app.middleware.auth_middleware import get_current_user
from app.services.export_service import ExportDataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["Data Export & Portability"])

@router.get("/pdf")
async def export_pdf(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Export all authenticated user nutrition, profile, targets, and meal history
    as a professional, multi-page PDF report.
    """
    try:
        snapshot = await ExportDataService.get_normalized_export_snapshot(session, current_user.id)
        pdf_bytes = ExportDataService.generate_pdf(snapshot)
        
        date_str = snapshot.get("export_metadata", {}).get("export_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        filename = f"NutriQ_Nutrition_Report_{date_str}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        logger.error(f"PDF Export error for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to export your data right now. Please try again."
        )

@router.get("/csv")
async def export_csv(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Export all authenticated user meal items, portions, calories, and macros
    as a spreadsheet-compatible CSV encoded with UTF-8 BOM.
    """
    try:
        snapshot = await ExportDataService.get_normalized_export_snapshot(session, current_user.id)
        csv_text = ExportDataService.generate_csv(snapshot)
        
        # utf-8-sig encodes with BOM for native Microsoft Excel and Google Sheets compatibility
        csv_bytes = csv_text.encode("utf-8-sig")
        
        date_str = snapshot.get("export_metadata", {}).get("export_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        filename = f"NutriQ_Nutrition_Data_{date_str}.csv"
        
        return Response(
            content=csv_bytes,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        logger.error(f"CSV Export error for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to export your data right now. Please try again."
        )

@router.get("/json")
async def export_json(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Export a complete structured digital backup of the authenticated user's data.
    """
    try:
        snapshot = await ExportDataService.get_normalized_export_snapshot(session, current_user.id)
        json_text = ExportDataService.generate_json(snapshot)
        
        date_str = snapshot.get("export_metadata", {}).get("export_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        filename = f"NutriQ_Data_Backup_{date_str}.json"
        
        return Response(
            content=json_text.encode("utf-8"),
            media_type="application/json; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        logger.error(f"JSON Export error for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to export your data right now. Please try again."
        )
