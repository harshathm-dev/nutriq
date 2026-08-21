from sqlalchemy import Column, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship as sa_relationship
from app.database.session import Base
from app.models.base import generate_uuid, utc_now

class Allergy(Base):
    __tablename__ = "allergies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    family_profile_id = Column(String(36), nullable=True)
    allergen_type = Column(String(100), nullable=False)  # "Dairy / Lactose", "Gluten", "Peanuts", "Tree Nuts", "Shellfish", "Soy", "Eggs"
    severity = Column(String(50), default="moderate", nullable=False)  # "mild", "moderate", "severe"
    notes = Column(Text, default="", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = sa_relationship("User", back_populates="allergies")
