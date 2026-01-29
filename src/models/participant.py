"""Participant Pydantic models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ParticipantBase(BaseModel):
    """Base participant fields."""

    user_id: UUID
    conversation_id: UUID


class ParticipantCreate(ParticipantBase):
    """Fields for adding a participant."""

    pass


class Participant(ParticipantBase):
    """Full participant model."""

    joined_at: datetime
    last_read_at: datetime | None = None

    class Config:
        from_attributes = True
