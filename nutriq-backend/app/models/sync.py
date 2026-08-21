from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.models.base import generate_uuid, utc_now

class DeviceSyncState(Base):
    __tablename__ = "device_sync_state"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    device_id = Column(String(100), nullable=False)
    last_sync_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    cursor = Column(String(100), default="0", nullable=False)
    status = Column(String(50), default="active", nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "device_id", name="uq_user_device_sync"),
    )

class SyncRecord(Base):
    __tablename__ = "sync_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    device_id = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)  # "meal", "water", "exercise", "weight"
    entity_id = Column(String(36), nullable=False)
    operation = Column(String(20), nullable=False)  # "INSERT", "UPDATE", "DELETE"
    payload = Column(Text, nullable=False)  # JSON payload
    client_timestamp = Column(DateTime(timezone=True), nullable=False)
    server_timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    status = Column(String(50), default="synced", nullable=False)  # "pending", "synced", "conflict_resolved"

    user = relationship("User", back_populates="sync_records")
