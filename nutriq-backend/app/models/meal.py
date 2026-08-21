from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.models.base import generate_uuid, TimestampMixin, utc_now

class Meal(Base, TimestampMixin):
    __tablename__ = "meals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    
    meal_type = Column(String(50), nullable=False)  # "breakfast", "mid_morning_snack", "lunch", "evening_snack", "dinner", "other"
    occurred_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    source = Column(String(50), default="manual", nullable=False)  # "manual", "ai_text", "voice", "image", "barcode", "template"
    sync_version = Column(Integer, default=1, nullable=False)

    user = relationship("User", back_populates="meals")
    items = relationship("MealItem", back_populates="meal", cascade="all, delete-orphan")

class MealItem(Base):
    __tablename__ = "meal_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    meal_id = Column(String(36), ForeignKey("meals.id", ondelete="CASCADE"), index=True, nullable=False)
    food_id = Column(String(36), ForeignKey("foods.id"), nullable=True)
    
    food_name = Column(String(255), nullable=False)
    quantity = Column(Float, default=1.0, nullable=False)
    serving_unit = Column(String(50), default="serving", nullable=False)
    grams = Column(Float, default=100.0, nullable=False)
    calories = Column(Float, nullable=False)
    protein_g = Column(Float, default=0.0, nullable=False)
    carbs_g = Column(Float, default=0.0, nullable=False)
    fat_g = Column(Float, default=0.0, nullable=False)
    fiber_g = Column(Float, default=0.0, nullable=False)
    sugar_g = Column(Float, default=0.0, nullable=False)
    sodium_mg = Column(Float, default=0.0, nullable=False)

    meal = relationship("Meal", back_populates="items")
    food = relationship("Food", back_populates="meal_items")

class FavoriteMeal(Base):
    __tablename__ = "favorite_meals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    meal_type = Column(String(50), default="breakfast", nullable=False)
    template_payload = Column(Text, nullable=False)  # JSON list of items
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="favorite_meals")

class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="", nullable=False)
    servings = Column(Integer, default=1, nullable=False)
    total_calories = Column(Float, default=0.0, nullable=False)
    total_protein_g = Column(Float, default=0.0, nullable=False)
    total_carbs_g = Column(Float, default=0.0, nullable=False)
    total_fat_g = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="recipes")
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")

class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    recipe_id = Column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), index=True, nullable=False)
    food_id = Column(String(36), ForeignKey("foods.id"), nullable=True)
    food_name = Column(String(255), nullable=False)
    quantity = Column(Float, default=1.0, nullable=False)
    unit = Column(String(50), default="g", nullable=False)
    grams = Column(Float, default=100.0, nullable=False)

    recipe = relationship("Recipe", back_populates="ingredients")
