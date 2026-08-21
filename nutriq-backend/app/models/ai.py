from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.models.base import generate_uuid, utc_now

class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    recommendation_type = Column(String(50), default="general", nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)  # JSON payload or text
    metadata_json = Column(Text, default="{}", nullable=False)
    status = Column(String(50), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="ai_recommendations")

class AIWarning(Base):
    __tablename__ = "ai_warnings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    warning_id = Column(String(100), nullable=False)  # "excess_calorie_warning", "low_protein_warning", "repeated_excess_warning"
    type = Column(String(50), nullable=False)  # "calorie_excess", "macro_imbalance", "trend"
    severity = Column(String(50), default="medium", nullable=False)  # "low", "medium", "high"
    message = Column(Text, nullable=False)
    evidence = Column(Text, default="{}", nullable=False)  # JSON data supporting warning
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="ai_warnings")

class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    plan_payload = Column(Text, nullable=False)  # JSON days & meals structure
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="meal_plans")

class AIInteractionLog(Base):
    __tablename__ = "ai_interaction_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    endpoint = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    input_hash = Column(String(64), nullable=False, index=True)
    request_metadata = Column(Text, default="{}", nullable=False)
    response_metadata = Column(Text, default="{}", nullable=False)
    latency_ms = Column(Integer, default=0, nullable=False)
    token_usage = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="ai_interaction_logs")

class AIUsageCounter(Base):
    __tablename__ = "ai_usage_counters"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    endpoint = Column(String(100), nullable=False)
    usage_date = Column(String(10), nullable=False)  # "YYYY-MM-DD"
    count = Column(Integer, default=1, nullable=False)

    user = relationship("User", back_populates="ai_usage_counters")

    __table_args__ = (
        UniqueConstraint("user_id", "endpoint", "usage_date", name="uq_user_endpoint_usage_date"),
    )
