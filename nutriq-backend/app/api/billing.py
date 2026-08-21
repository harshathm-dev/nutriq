from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database.session import get_db
from app.models.user import User
from app.models.billing import Subscription, Entitlement
from app.schemas.billing import SubscriptionOut, PlanSubscribeRequest
from app.middleware.auth_middleware import get_current_user
from app.services.billing_service import BillingService

router = APIRouter(prefix="/billing", tags=["Subscription & Billing"])

@router.get("/plan", response_model=SubscriptionOut)
async def get_billing_plan(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    sub = await BillingService.get_or_create_subscription(session, current_user.id)
    stmt = select(Subscription).where(Subscription.id == sub.id).options(selectinload(Subscription.entitlements))
    res = await session.execute(stmt)
    sub = res.scalar_one()

    daily_limit = 200 if sub.plan_tier == "premium" else 15
    return SubscriptionOut(
        id=sub.id,
        user_id=sub.user_id,
        plan_tier=sub.plan_tier,
        billing_status=sub.billing_status,
        current_period_end=sub.current_period_end,
        entitlements=sub.entitlements,
        used_today_ai_calls=2,
        daily_limit=daily_limit
    )

@router.post("/subscribe", response_model=SubscriptionOut)
async def subscribe_plan(
    req: PlanSubscribeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    sub = await BillingService.update_subscription_plan(session, current_user.id, req.plan_tier)
    stmt = select(Subscription).where(Subscription.id == sub.id).options(selectinload(Subscription.entitlements))
    res = await session.execute(stmt)
    sub = res.scalar_one()
    daily_limit = 200 if sub.plan_tier == "premium" else 15
    return SubscriptionOut(
        id=sub.id,
        user_id=sub.user_id,
        plan_tier=sub.plan_tier,
        billing_status=sub.billing_status,
        current_period_end=sub.current_period_end,
        entitlements=sub.entitlements,
        used_today_ai_calls=0,
        daily_limit=daily_limit
    )

@router.post("/cancel", response_model=SubscriptionOut)
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    sub = await BillingService.update_subscription_plan(session, current_user.id, "free")
    stmt = select(Subscription).where(Subscription.id == sub.id).options(selectinload(Subscription.entitlements))
    res = await session.execute(stmt)
    sub = res.scalar_one()
    return SubscriptionOut(
        id=sub.id,
        user_id=sub.user_id,
        plan_tier=sub.plan_tier,
        billing_status=sub.billing_status,
        current_period_end=sub.current_period_end,
        entitlements=sub.entitlements,
        used_today_ai_calls=0,
        daily_limit=15
    )
