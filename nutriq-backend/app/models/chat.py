from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Index
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.models.base import generate_uuid, utc_now


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String(255), default="New Conversation", nullable=False)
    summary = Column(Text, nullable=True)  # Optional long-term conversation memory
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at.asc()"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    role = Column(String(50), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)  # Recommendations, warnings, macros, sources
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User", back_populates="chat_messages")

    __table_args__ = (
        Index("ix_chat_message_session_created", "session_id", "created_at"),
        Index("ix_chat_message_user_created", "user_id", "created_at"),
    )
