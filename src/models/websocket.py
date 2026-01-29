"""WebSocket message schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class WSMessageType(str, Enum):
    """WebSocket message types."""

    # Client -> Server
    SEND_MESSAGE = "send_message"
    TYPING_START = "typing_start"
    TYPING_STOP = "typing_stop"
    MARK_READ = "mark_read"

    # Server -> Client
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_STATUS = "message_status"
    TYPING_INDICATOR = "typing_indicator"
    PRESENCE_UPDATE = "presence_update"
    ERROR = "error"


# Client -> Server payloads


class SendMessagePayload(BaseModel):
    """Payload for send_message."""

    conversation_id: UUID = Field(..., alias="conversationId")
    content: str = Field(..., min_length=1, max_length=10000)
    client_message_id: UUID = Field(..., alias="clientMessageId")

    class Config:
        populate_by_name = True


class TypingPayload(BaseModel):
    """Payload for typing_start/typing_stop."""

    conversation_id: UUID = Field(..., alias="conversationId")

    class Config:
        populate_by_name = True


class MarkReadPayload(BaseModel):
    """Payload for mark_read."""

    conversation_id: UUID = Field(..., alias="conversationId")
    message_id: UUID = Field(..., alias="messageId")

    class Config:
        populate_by_name = True


# Server -> Client payloads


class MessageReceivedPayload(BaseModel):
    """Payload for message_received."""

    id: UUID
    conversation_id: UUID = Field(..., alias="conversationId")
    sender_id: UUID = Field(..., alias="senderId")
    content: str
    created_at: datetime = Field(..., alias="createdAt")
    status: str

    class Config:
        populate_by_name = True


class MessageStatusPayload(BaseModel):
    """Payload for message_status."""

    message_id: UUID = Field(..., alias="messageId")
    status: str
    client_message_id: UUID = Field(..., alias="clientMessageId")

    class Config:
        populate_by_name = True


class TypingIndicatorPayload(BaseModel):
    """Payload for typing_indicator."""

    conversation_id: UUID = Field(..., alias="conversationId")
    user_id: UUID = Field(..., alias="userId")
    is_typing: bool = Field(..., alias="isTyping")

    class Config:
        populate_by_name = True


class PresenceUpdatePayload(BaseModel):
    """Payload for presence_update."""

    user_id: UUID = Field(..., alias="userId")
    status: str
    last_seen: datetime | None = Field(None, alias="lastSeen")

    class Config:
        populate_by_name = True


class ErrorPayload(BaseModel):
    """Payload for error."""

    code: str
    message: str
    original_type: str | None = Field(None, alias="originalType")

    class Config:
        populate_by_name = True


class WSMessage(BaseModel):
    """Generic WebSocket message wrapper."""

    type: WSMessageType
    payload: dict
