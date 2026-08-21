from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.models.base import generate_uuid, utc_now

class Exercise(Base):
    __tablename__ = "exercise"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    type = Column(String(100), nullable=False)  # "walking", "running", "cycling", "gym_workout", "strength", "cardio", "sports", "yoga", "swimming", "household", "other"
    duration_min = Column(Integer, nullable=False)
    intensity = Column(String(50), default="moderate", nullable=False)  # "low", "moderate", "high"
    calories_burned_est = Column(Float, default=0.0, nullable=False)
    steps = Column(Integer, default=0, nullable=True)
    distance_km = Column(Float, default=0.0, nullable=True)
    notes = Column(String(500), nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="exercises")

class Water(Base):
    __tablename__ = "water"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    amount_ml = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="water_logs")

class WeightHistory(Base):
    __tablename__ = "weight_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    weight_kg = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="weight_logs")
