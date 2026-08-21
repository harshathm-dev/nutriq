from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.models.base import generate_uuid, TimestampMixin


class MealReminderSetting(Base, TimestampMixin):
    __tablename__ = "meal_reminder_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)

    reminders_enabled = Column(Boolean, default=True, nullable=False)

    breakfast_enabled = Column(Boolean, default=True, nullable=False)
    breakfast_time = Column(String(10), default="08:00", nullable=False)

    lunch_enabled = Column(Boolean, default=True, nullable=False)
    lunch_time = Column(String(10), default="13:00", nullable=False)

    snack_enabled = Column(Boolean, default=True, nullable=False)
    snack_time = Column(String(10), default="17:00", nullable=False)

    dinner_enabled = Column(Boolean, default=True, nullable=False)
    dinner_time = Column(String(10), default="20:00", nullable=False)

    grace_period_minutes = Column(Integer, default=30, nullable=False)

    daily_summary_enabled = Column(Boolean, default=True, nullable=False)
    daily_summary_time = Column(String(10), default="20:30", nullable=False)

    user_timezone = Column(String(50), default="Asia/Kolkata", nullable=False)

    user = relationship("User", back_populates="reminder_setting")


class MealReminderLog(Base, TimestampMixin):
    __tablename__ = "meal_reminder_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    meal_type = Column(String(50), nullable=False)  # "breakfast", "lunch", "snack", "dinner", "daily_summary"
    date = Column(String(10), index=True, nullable=False)  # "YYYY-MM-DD"
    reminder_sent = Column(Boolean, default=False, nullable=False)
    remind_later_count = Column(Integer, default=0, nullable=False)  # Max 2
    dismissed = Column(Boolean, default=False, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    last_reminded_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="reminder_logs")
