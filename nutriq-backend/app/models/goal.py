from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.models.base import generate_uuid, TimestampMixin

class Goal(Base, TimestampMixin):
    __tablename__ = "goals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    
    goal_type = Column(String(50), nullable=False)  # "weight_loss", "maintain", "weight_gain", "muscle_building"
    current_weight_kg = Column(Float, nullable=False)
    target_weight_kg = Column(Float, nullable=False)
    desired_rate = Column(Float, default=0.5, nullable=False)  # kg per week change
    target_date = Column(DateTime(timezone=True), nullable=True)
    active = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="goals")
