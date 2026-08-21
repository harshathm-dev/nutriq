from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ChatMessageBase(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str


class ChatMessageCreate(BaseModel):
    session_id: Optional[str] = None
    content: str
    stream: bool = True


class ConversationMessageCreate(BaseModel):
    content: str
    stream: bool = True


class ChatMessageOut(ChatMessageBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    messageId: Optional[str] = None
    session_id: str
    conversationId: Optional[str] = None
    user_id: str
    userId: Optional[str] = None
    metadata_json: Optional[str] = "{}"
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    timestamp: Optional[datetime] = None


class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Conversation"


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"


class ConversationUpdate(BaseModel):
    title: str


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversationId: Optional[str] = None
    user_id: str
    userId: Optional[str] = None
    title: str
    summary: Optional[str] = None
    created_at: datetime
    createdAt: Optional[datetime] = None
    updated_at: datetime
    updatedAt: Optional[datetime] = None
    message_count: int = 0
    last_message_preview: Optional[str] = None


class ChatSessionDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversationId: Optional[str] = None
    user_id: str
    userId: Optional[str] = None
    title: str
    summary: Optional[str] = None
    created_at: datetime
    createdAt: Optional[datetime] = None
    updated_at: datetime
    updatedAt: Optional[datetime] = None
    messages: List[ChatMessageOut] = []


# Aliases for explicit RESTful conversation endpoints
ConversationOut = ChatSessionOut
ConversationDetailOut = ChatSessionDetailOut
