from app.models.base import Base, generate_uuid, utc_now, TimestampMixin
from app.models.user import User
from app.models.profile import UserProfile
from app.models.goal import Goal
from app.models.food import Food, ServingConversion, CustomFood, UserFavoriteFood
from app.models.meal import Meal, MealItem, FavoriteMeal, Recipe, RecipeIngredient
from app.models.tracking import Exercise, Water, WeightHistory
from app.models.ai import AIRecommendation, AIWarning, MealPlan, AIInteractionLog, AIUsageCounter
from app.models.billing import Subscription, Entitlement
from app.models.privacy import ConsentRecord
from app.models.family import Allergy
from app.models.reminder import MealReminderSetting, MealReminderLog
from app.models.audit import AuditLog
from app.models.auth import PasswordResetToken
from app.models.sync import DeviceSyncState, SyncRecord
from app.models.chat import ChatSession, ChatMessage
from app.models.streak import UserStreak

__all__ = [
    "Base",
    "generate_uuid",
    "utc_now",
    "TimestampMixin",
    "User",
    "PasswordResetToken",
    "UserProfile",
    "Goal",
    "Food",
    "ServingConversion",
    "CustomFood",
    "UserFavoriteFood",
    "Meal",
    "MealItem",
    "FavoriteMeal",
    "Recipe",
    "RecipeIngredient",
    "Exercise",
    "Water",
    "WeightHistory",
    "AIRecommendation",
    "AIWarning",
    "MealPlan",
    "AIInteractionLog",
    "AIUsageCounter",
    "Subscription",
    "Entitlement",
    "ConsentRecord",
    "Allergy",
    "DeviceSyncState",
    "SyncRecord",
    "AuditLog",
    "MealReminderSetting",
    "MealReminderLog",
    "ChatSession",
    "ChatMessage",
    "UserStreak",
]
