"""REST endpoints for message history."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from src.api.dependencies import DBConnection
from src.api.middleware.auth import CurrentUserId
from src.api.middleware.errors import NotFoundError, UnauthorizedError
from src.models.message import Message, MessageList
from src.services.history import history_service
from src.services.chat import chat_service

router = APIRouter()


class SendMessageRequest(BaseModel):
    """Request body for sending a message via REST."""

    content: str = Field(..., min_length=1, max_length=10000)
    client_message_id: UUID | None = Field(None, alias="clientMessageId")

    class Config:
        populate_by_name = True


@router.get("/conversations/{conversation_id}/messages", response_model=MessageList)
async def get_messages(
    conversation_id: UUID,
    current_user_id: CurrentUserId,
    limit: int = Query(default=50, le=100),
    before: UUID | None = Query(default=None),
) -> MessageList:
    """Get message history for a conversation."""
    # Verify user is participant
    if not await chat_service.verify_participant(current_user_id, conversation_id):
        raise UnauthorizedError("Not a participant in this conversation")

    return await history_service.get_messages(
        conversation_id=conversation_id,
        limit=limit,
        before=before,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=Message,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: UUID,
    request: SendMessageRequest,
    current_user_id: CurrentUserId,
) -> Message:
    """Send a message via REST (fallback for WebSocket)."""
    client_message_id = request.client_message_id or uuid4()

    return await chat_service.send_message(
        user_id=current_user_id,
        conversation_id=conversation_id,
        content=request.content,
        client_message_id=client_message_id,
    )
