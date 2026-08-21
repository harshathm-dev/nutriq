from sqlalchemy import Column, String, ForeignKey, DateTime, Text
from app.database.session import Base
from app.models.base import generate_uuid, utc_now

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    admin_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)  # "CREATE_FOOD", "UPDATE_FOOD", "DELETE_USER", "UPDATE_CONFIG"
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
