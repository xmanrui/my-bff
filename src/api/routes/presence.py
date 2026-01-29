"""REST endpoints for user presence."""

from uuid import UUID

from fastapi import APIRouter

from src.api.middleware.auth import CurrentUserId
from src.models.presence import Presence
from src.services.presence import presence_service

router = APIRouter()


@router.get("/users/{user_id}/presence", response_model=Presence)
async def get_user_presence(
    user_id: UUID,
    current_user_id: CurrentUserId,
) -> Presence:
    """Get user presence status."""
    return await presence_service.get_presence(user_id)
