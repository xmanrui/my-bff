"""REST endpoints for conversations."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query, HTTPException, status

from src.api.middleware.auth import CurrentUserId
from src.models.conversation import (
    Conversation,
    ConversationCreate,
    ConversationList,
)
from src.services.conversation import conversation_service

router = APIRouter()


@router.post("/conversations", response_model=Conversation, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_user_id: CurrentUserId,
) -> Conversation:
    """Create a new conversation."""
    return await conversation_service.create_conversation(
        creator_id=current_user_id,
        data=data,
    )


@router.get("/conversations", response_model=ConversationList)
async def list_conversations(
    current_user_id: CurrentUserId,
    limit: int = Query(default=20, ge=1, le=100),
    before: str | None = Query(default=None),
) -> ConversationList:
    """List user's conversations sorted by most recent activity."""
    before_dt = None
    if before:
        try:
            before_dt = datetime.fromisoformat(before)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cursor format",
            )

    return await conversation_service.get_user_conversations(
        user_id=current_user_id,
        limit=limit,
        before=before_dt,
    )


@router.get("/conversations/search", response_model=list[Conversation])
async def search_conversations(
    current_user_id: CurrentUserId,
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[Conversation]:
    """Search conversations by name or message content."""
    return await conversation_service.search_conversations(
        user_id=current_user_id,
        query=q,
        limit=limit,
    )


@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: UUID,
    current_user_id: CurrentUserId,
) -> Conversation:
    """Get a specific conversation."""
    conversation = await conversation_service.get_conversation(
        conversation_id=conversation_id,
        user_id=current_user_id,
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conversation
