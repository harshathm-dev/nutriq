from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.models.base import generate_uuid, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # nullable for OAuth users
    role = Column(String(50), default="user", nullable=False)  # "user", "admin"
    auth_provider = Column(String(50), default="email", nullable=False)  # "email", "google"
    google_id = Column(String(255), unique=True, index=True, nullable=True)
    welcome_email_sent = Column(Boolean, default=False, nullable=False)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    meals = relationship("Meal", back_populates="user", cascade="all, delete-orphan")
    exercises = relationship("Exercise", back_populates="user", cascade="all, delete-orphan")
    water_logs = relationship("Water", back_populates="user", cascade="all, delete-orphan")
    weight_logs = relationship("WeightHistory", back_populates="user", cascade="all, delete-orphan")
    ai_recommendations = relationship("AIRecommendation", back_populates="user", cascade="all, delete-orphan")
    ai_warnings = relationship("AIWarning", back_populates="user", cascade="all, delete-orphan")
    meal_plans = relationship("MealPlan", back_populates="user", cascade="all, delete-orphan")
    ai_interaction_logs = relationship("AIInteractionLog", back_populates="user", cascade="all, delete-orphan")
    ai_usage_counters = relationship("AIUsageCounter", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sync_records = relationship("SyncRecord", back_populates="user", cascade="all, delete-orphan")
    custom_foods = relationship("CustomFood", back_populates="user", cascade="all, delete-orphan")
    favorite_foods = relationship("UserFavoriteFood", back_populates="user", cascade="all, delete-orphan")
    favorite_meals = relationship("FavoriteMeal", back_populates="user", cascade="all, delete-orphan")
    recipes = relationship("Recipe", back_populates="user", cascade="all, delete-orphan")
    allergies = relationship("Allergy", back_populates="user", cascade="all, delete-orphan")
    consent_records = relationship("ConsentRecord", back_populates="user", cascade="all, delete-orphan")
    reminder_setting = relationship("MealReminderSetting", back_populates="user", uselist=False, cascade="all, delete-orphan")
    reminder_logs = relationship("MealReminderLog", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    streak = relationship("UserStreak", back_populates="user", uselist=False, cascade="all, delete-orphan")
