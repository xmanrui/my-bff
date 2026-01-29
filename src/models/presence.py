"""Presence Pydantic models."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class PresenceStatus(str, Enum):
    """User presence status."""

    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"


class Presence(BaseModel):
    """User presence information."""

    status: PresenceStatus
    last_seen: datetime | None = None


class PresenceUpdate(BaseModel):
    """Presence update event."""

    user_id: UUID
    status: PresenceStatus
    last_seen: datetime | None = None
