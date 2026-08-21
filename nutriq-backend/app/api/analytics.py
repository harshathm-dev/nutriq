from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.user import User
from app.middleware.auth_middleware import get_current_user
from app.services.analytics_service import AnalyticsService
from app.services.warning_engine import WarningEngine
from app.services.agent_service import ReportAgent
from app.schemas.analytics import AnalyticsRangeResponse

router = APIRouter(prefix="/analytics", tags=["Analytics & Progress Intelligence"])

@router.get("", response_model=AnalyticsRangeResponse)
async def get_analytics_overview(
    range: str = Query("7d", description="Time range: '7d', '30d', '90d', or 'custom'"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD) for custom range"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD) for custom range"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Main Analytics Endpoint.
    Returns complete, grounded nutrition, hydration, macro, activity, calorie balance,
    and weight progress metrics across the requested timeframe.
    """
    analytics_data = await AnalyticsService.get_analytics_range(
        session=session,
        user_id=current_user.id,
        range_key=range,
        start_date_str=start_date,
        end_date_str=end_date
    )
    return analytics_data


@router.get("/daily")
async def get_daily_analytics(
    date_str: Optional[str] = Query(None, alias="date"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    analytics = await AnalyticsService.get_daily_analytics(session, current_user.id, date_str)
    
    # Evaluate warnings
    warnings = WarningEngine.evaluate_warnings(
        consumed_calories=analytics["consumed"]["calories"],
        target_calories=analytics["targets"]["target_calories"],
        consumed_protein_g=analytics["consumed"]["protein_g"],
        target_protein_g=analytics["targets"]["protein_g"],
        fitness_goal="maintain",
        recent_days_calorie_history=[analytics["consumed"]["calories"]]
    )
    analytics["warnings"] = warnings
    return analytics


@router.get("/weekly")
async def get_weekly_analytics(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    full_analytics = await AnalyticsService.get_analytics_range(
        session=session,
        user_id=current_user.id,
        range_key="7d"
    )

    daily_breakdown = []
    for c, h, a in zip(full_analytics["calories"], full_analytics["hydration"], full_analytics["activity"]):
        daily_breakdown.append({
            "day": c["display_date"],
            "date": c["date"],
            "calories": c["consumed"],
            "target_calories": c["target"],
            "protein_g": next((p["consumed_g"] for p in full_analytics["protein"] if p["date"] == c["date"]), 0.0),
            "water_ml": h["consumed_ml"],
            "burned_calories": a["calories_burned"]
        })

    report_agent = ReportAgent()
    weekly_report = report_agent.run({
        "avg_calories": full_analytics["summary"]["avg_calories"],
        "target_calories": full_analytics["summary"]["target_calories"],
        "avg_protein_g": full_analytics["summary"]["avg_protein"],
        "target_protein_g": full_analytics["summary"]["target_protein"]
    })

    return {
        "has_data": full_analytics["summary"]["has_data"],
        "daily_breakdown": daily_breakdown,
        "weekly_averages": {
            "avg_daily_calories": full_analytics["summary"]["avg_calories"],
            "avg_daily_protein_g": full_analytics["summary"]["avg_protein"],
            "avg_daily_water_ml": round(full_analytics["summary"]["avg_water_liters"] * 1000, 1),
            "adherence_percentage": full_analytics["summary"]["goal_adherence_pct"],
            "total_weekly_calories": round(sum(d["calories"] for d in daily_breakdown), 1)
        },
        "weight_history": full_analytics["weight_progress"]["history"],
        "ai_report": weekly_report
    }


@router.get("/monthly")
async def get_monthly_analytics(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    monthly_analytics = await AnalyticsService.get_analytics_range(
        session=session,
        user_id=current_user.id,
        range_key="30d"
    )
    return {
        "period": "Last 30 Days",
        "adherence_score": int(monthly_analytics["summary"]["goal_adherence_pct"]),
        "weight_change_kg": monthly_analytics["weight_progress"]["weight_change_kg"] or 0.0,
        "total_active_days": monthly_analytics["summary"]["total_tracked_days"],
        "total_calories_logged": round(sum(c["consumed"] for c in monthly_analytics["calories"]), 1),
        "average_hydration_pct": int(monthly_analytics["hydration_summary"]["days_goal_achieved"] / max(1, monthly_analytics["summary"]["total_tracked_days"]) * 100) if monthly_analytics["summary"]["total_tracked_days"] > 0 else 0
    }
