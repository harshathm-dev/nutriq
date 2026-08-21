from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, Index
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.models.base import generate_uuid, utc_now


class UserStreak(Base):
    __tablename__ = "user_streaks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    current_streak = Column(Integer, default=0, nullable=False)
    longest_streak = Column(Integer, default=0, nullable=False)
    last_completed_date = Column(String(10), nullable=True)  # Format: "YYYY-MM-DD"
    total_active_days = Column(Integer, default=0, nullable=False)
    milestones_achieved_json = Column(Text, default="[]", nullable=False)  # e.g. "[3, 7, 14]"
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="streak")

    __table_args__ = (
        Index("ix_user_streak_user_id", "user_id"),
    )
