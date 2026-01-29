"""History service for message retrieval."""

import logging
from uuid import UUID

from src.db.connection import get_connection
from src.models.message import Message, MessageStatus, MessageList

logger = logging.getLogger("chat.services.history")

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


class HistoryService:
    """Service for message history operations."""

    async def get_messages(
        self,
        conversation_id: UUID,
        limit: int = DEFAULT_LIMIT,
        before: UUID | None = None,
    ) -> MessageList:
        """Get messages for a conversation with cursor-based pagination."""
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT

        async with get_connection() as conn:
            if before:
                # Get the created_at of the cursor message
                cursor_time = await conn.fetchval(
                    "SELECT created_at FROM messages WHERE id = $1",
                    before,
                )
                if cursor_time:
                    rows = await conn.fetch(
                        """
                        SELECT id, conversation_id, sender_id, content,
                               created_at, status
                        FROM messages
                        WHERE conversation_id = $1
                          AND created_at < $2
                        ORDER BY created_at DESC
                        LIMIT $3
                        """,
                        conversation_id,
                        cursor_time,
                        limit + 1,  # Fetch one extra to check has_more
                    )
                else:
                    rows = []
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, conversation_id, sender_id, content,
                           created_at, status
                    FROM messages
                    WHERE conversation_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    conversation_id,
                    limit + 1,
                )

            has_more = len(rows) > limit
            if has_more:
                rows = rows[:limit]

            # Convert to Message objects (reverse to chronological order)
            messages = [
                Message(
                    id=row["id"],
                    conversation_id=row["conversation_id"],
                    sender_id=row["sender_id"],
                    content=row["content"],
                    created_at=row["created_at"],
                    status=MessageStatus(row["status"]),
                )
                for row in reversed(rows)
            ]

            return MessageList(messages=messages, has_more=has_more)

    async def get_message_by_id(
        self, message_id: UUID
    ) -> Message | None:
        """Get a single message by ID."""
        async with get_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, conversation_id, sender_id, content,
                       created_at, status
                FROM messages
                WHERE id = $1
                """,
                message_id,
            )
            if row:
                return Message(
                    id=row["id"],
                    conversation_id=row["conversation_id"],
                    sender_id=row["sender_id"],
                    content=row["content"],
                    created_at=row["created_at"],
                    status=MessageStatus(row["status"]),
                )
            return None


# Singleton instance
history_service = HistoryService()
