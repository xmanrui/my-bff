"""Message Pydantic models."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class MessageStatus(str, Enum):
    """Message delivery status."""

    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class MessageBase(BaseModel):
    """Base message fields."""

    content: str = Field(..., min_length=1, max_length=10000)


class MessageCreate(MessageBase):
    """Fields for creating a message."""

    conversation_id: UUID


class SendMessage(MessageBase):
    """Request body for sending a message."""

    pass


class Message(MessageBase):
    """Full message model."""

    id: UUID
    conversation_id: UUID
    sender_id: UUID
    created_at: datetime
    status: MessageStatus = MessageStatus.SENT

    class Config:
        from_attributes = True


class MessageList(BaseModel):
    """Paginated list of messages."""

    messages: list[Message]
    has_more: bool
