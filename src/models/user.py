"""User Pydantic models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Base user fields."""

    display_name: str = Field(..., max_length=100)
    avatar_url: str | None = Field(None, max_length=500)


class UserCreate(UserBase):
    """Fields for creating a user."""

    pass


class User(UserBase):
    """Full user model with all fields."""

    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class UserInConversation(BaseModel):
    """User info as shown in conversation context."""

    id: UUID
    display_name: str
    avatar_url: str | None = None
