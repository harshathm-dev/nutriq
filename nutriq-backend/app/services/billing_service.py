from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.billing import Subscription, Entitlement

class BillingService:
    @classmethod
    async def get_or_create_subscription(cls, session: AsyncSession, user_id: str) -> Subscription:
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        res = await session.execute(stmt)
        sub = res.scalar_one_or_none()
        if not sub:
            sub = Subscription(
                user_id=user_id,
                plan_tier="free",
                billing_status="active",
                current_period_end=datetime.now(timezone.utc) + timedelta(days=365)
            )
            session.add(sub)
            await session.flush()

            # Add default free entitlements
            session.add(Entitlement(subscription_id=sub.id, feature_key="ai_chat", daily_quota=15, is_enabled=1))
            session.add(Entitlement(subscription_id=sub.id, feature_key="meal_planning", daily_quota=2, is_enabled=1))
            session.add(Entitlement(subscription_id=sub.id, feature_key="vision_scan", daily_quota=5, is_enabled=1))
            await session.commit()
        return sub

    @classmethod
    async def update_subscription_plan(cls, session: AsyncSession, user_id: str, plan_tier: str) -> Subscription:
        sub = await cls.get_or_create_subscription(session, user_id)
        sub.plan_tier = plan_tier
        sub.billing_status = "active"
        sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
        await session.commit()
        return sub
