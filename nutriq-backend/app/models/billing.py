from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.models.base import generate_uuid, TimestampMixin, utc_now

class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    plan_tier = Column(String(50), default="free", nullable=False)  # "free", "premium", "family"
    billing_status = Column(String(50), default="active", nullable=False)  # "active", "cancelled", "past_due"
    current_period_end = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="subscription")
    entitlements = relationship("Entitlement", back_populates="subscription", cascade="all, delete-orphan")

class Entitlement(Base):
    __tablename__ = "entitlements"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True, nullable=False)
    feature_key = Column(String(100), nullable=False)  # "ai_chat", "vision_scan", "meal_planning", "voice_logging"
    daily_quota = Column(Integer, default=15, nullable=False)
    is_enabled = Column(Integer, default=1, nullable=False)

    subscription = relationship("Subscription", back_populates="entitlements")
