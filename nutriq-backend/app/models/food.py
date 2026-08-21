from sqlalchemy import Column, String, Float, Boolean, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.models.base import generate_uuid, utc_now

class Food(Base):
    __tablename__ = "foods"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), nullable=True, index=True)  # e.g. "IND-0001", "SIF-0001"
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True, index=True)
    region = Column(String(100), nullable=True, index=True)
    serving_size_desc = Column(String(100), nullable=True)  # e.g. "2 pieces (~80g)", "1 piece (~90g)"
    serving_size = Column(Float, default=100.0, nullable=False)
    unit = Column(String(50), default="g", nullable=False)
    calories = Column(Float, nullable=False)
    protein_g = Column(Float, default=0.0, nullable=False)
    carbs_g = Column(Float, default=0.0, nullable=False)
    fat_g = Column(Float, default=0.0, nullable=False)
    fiber_g = Column(Float, default=0.0, nullable=False)
    sugar_g = Column(Float, default=0.0, nullable=False)
    sodium_mg = Column(Float, default=0.0, nullable=False)
    calcium_mg = Column(Float, nullable=True)
    iron_mg = Column(Float, nullable=True)
    vitamin_c_mg = Column(Float, nullable=True)
    folate_ug = Column(Float, nullable=True)
    source = Column(String(100), default="IFCT", nullable=False)  # "IFCT", "OpenFoodFacts", "Nutritionix", "System", "Existing NutriQ dataset", "South Indian food dataset"
    barcode = Column(String(100), nullable=True, index=True)
    normalized_key = Column(String(255), nullable=False, unique=True, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    serving_conversions = relationship("ServingConversion", back_populates="food", cascade="all, delete-orphan")
    meal_items = relationship("MealItem", back_populates="food")

    __table_args__ = (
        UniqueConstraint("normalized_key", name="uq_food_normalized_key"),
    )

class ServingConversion(Base):
    __tablename__ = "serving_conversions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    food_id = Column(String(36), ForeignKey("foods.id", ondelete="CASCADE"), index=True, nullable=False)
    serving_label = Column(String(100), nullable=False)  # "1 piece", "1 katori", "1 cup", "1 dosa", "1 glass"
    grams = Column(Float, nullable=False)
    unit = Column(String(50), default="g", nullable=False)

    food = relationship("Food", back_populates="serving_conversions")

    __table_args__ = (
        UniqueConstraint("food_id", "serving_label", name="uq_food_serving_label"),
    )

class CustomFood(Base):
    __tablename__ = "custom_foods"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), default="Custom", nullable=False)
    serving_size = Column(Float, default=100.0, nullable=False)
    unit = Column(String(50), default="g", nullable=False)
    calories = Column(Float, nullable=False)
    protein_g = Column(Float, default=0.0, nullable=False)
    carbs_g = Column(Float, default=0.0, nullable=False)
    fat_g = Column(Float, default=0.0, nullable=False)
    fiber_g = Column(Float, default=0.0, nullable=False)
    sugar_g = Column(Float, default=0.0, nullable=False)
    sodium_mg = Column(Float, default=0.0, nullable=False)
    is_private = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="custom_foods")


class UserFavoriteFood(Base):
    __tablename__ = "user_favorite_foods"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    food_id = Column(String(36), ForeignKey("foods.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="favorite_foods")
    food = relationship("Food")

    __table_args__ = (
        UniqueConstraint("user_id", "food_id", name="uq_user_food_favorite"),
    )


