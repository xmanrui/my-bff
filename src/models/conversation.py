"""Conversation Pydantic models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationBase(BaseModel):
    """Base conversation fields."""

    pass


class ConversationCreate(BaseModel):
    """Fields for creating a conversation."""

    participant_ids: list[UUID] = Field(..., min_length=1, max_length=1)


class Conversation(ConversationBase):
    """Full conversation model."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationWithDetails(Conversation):
    """Conversation with participants and last message."""

    from src.models.user import UserInConversation
    from src.models.message import Message

    participants: list[UserInConversation] = []
    last_message: "Message | None" = None
    unread_count: int = 0


class ConversationList(BaseModel):
    """Paginated list of conversations."""

    conversations: list[ConversationWithDetails]
    has_more: bool
    next_cursor: str | None = None
