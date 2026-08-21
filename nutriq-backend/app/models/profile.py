from sqlalchemy import Column, String, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.models.base import generate_uuid, TimestampMixin

class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    
    name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(50), nullable=False)  # "male", "female", "other"
    height_cm = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    activity_level = Column(String(50), default="moderately_active", nullable=False)  
    # "sedentary", "lightly_active", "moderately_active", "very_active", "extremely_active"
    fitness_goal = Column(String(50), default="maintain", nullable=False)
    # "weight_loss", "maintain", "weight_gain", "muscle_building"
    dietary_preference = Column(String(100), default="standard", nullable=False)
    # "standard", "vegetarian", "vegan", "keto", "pescatarian", "jain", "eggetarian"
    food_preferences = Column(Text, default="", nullable=True)  # comma-separated or json string

    user = relationship("User", back_populates="profile")
