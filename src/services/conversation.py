"""Conversation service for managing chat conversations."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from src.db.connection import get_db_pool
from src.models.conversation import (
    Conversation,
    ConversationCreate,
    ConversationList,
    ConversationType,
)
from src.models.participant import ParticipantRole

logger = logging.getLogger("chat.services.conversation")


class ConversationService:
    """Service for conversation operations."""

    async def create_conversation(
        self,
        creator_id: UUID,
        data: ConversationCreate,
    ) -> Conversation:
        """Create a new conversation with participants."""
        pool = get_db_pool()
        now = datetime.now(timezone.utc)

        async with pool.acquire() as conn:
            async with conn.transaction():
                # Create conversation
                row = await conn.fetchrow(
                    """
                    INSERT INTO conversations (name, type, created_at, updated_at)
                    VALUES ($1, $2, $3, $3)
                    RETURNING id, name, type, created_at, updated_at
                    """,
                    data.name,
                    data.type.value,
                    now,
                )

                conversation_id = row["id"]

                # Add creator as owner
                await conn.execute(
                    """
                    INSERT INTO participants
                    (conversation_id, user_id, role, joined_at)
                    VALUES ($1, $2, $3, $4)
                    """,
                    conversation_id,
                    creator_id,
                    ParticipantRole.OWNER.value,
                    now,
                )

                # Add other participants as members
                for participant_id in data.participant_ids:
                    if participant_id != creator_id:
                        await conn.execute(
                            """
                            INSERT INTO participants
                            (conversation_id, user_id, role, joined_at)
                            VALUES ($1, $2, $3, $4)
                            """,
                            conversation_id,
                            participant_id,
                            ParticipantRole.MEMBER.value,
                            now,
                        )

                logger.info(
                    f"Created conversation {conversation_id} "
                    f"with {len(data.participant_ids) + 1} participants"
                )

                return Conversation(
                    id=row["id"],
                    name=row["name"],
                    type=ConversationType(row["type"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

    async def get_user_conversations(
        self,
        user_id: UUID,
        limit: int = 20,
        before: datetime | None = None,
    ) -> ConversationList:
        """Get conversations for a user, sorted by updated_at DESC."""
        pool = get_db_pool()

        query = """
            SELECT c.id, c.name, c.type, c.created_at, c.updated_at
            FROM conversations c
            INNER JOIN participants p ON p.conversation_id = c.id
            WHERE p.user_id = $1
        """
        params: list = [user_id]

        if before:
            query += " AND c.updated_at < $2"
            params.append(before)

        query += " ORDER BY c.updated_at DESC LIMIT $" + str(len(params) + 1)
        params.append(limit + 1)

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        conversations = [
            Conversation(
                id=row["id"],
                name=row["name"],
                type=ConversationType(row["type"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows[:limit]
        ]

        has_more = len(rows) > limit
        next_cursor = None
        if has_more and conversations:
            next_cursor = conversations[-1].updated_at.isoformat()

        return ConversationList(
            conversations=conversations,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def get_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> Conversation | None:
        """Get a conversation by ID if user is a participant."""
        pool = get_db_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT c.id, c.name, c.type, c.created_at, c.updated_at
                FROM conversations c
                INNER JOIN participants p ON p.conversation_id = c.id
                WHERE c.id = $1 AND p.user_id = $2
                """,
                conversation_id,
                user_id,
            )

        if not row:
            return None

        return Conversation(
            id=row["id"],
            name=row["name"],
            type=ConversationType(row["type"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_unread_count(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> int:
        """Get unread message count for a user in a conversation."""
        pool = get_db_pool()

        async with pool.acquire() as conn:
            # Get user's last_read_at
            participant = await conn.fetchrow(
                """
                SELECT last_read_at FROM participants
                WHERE conversation_id = $1 AND user_id = $2
                """,
                conversation_id,
                user_id,
            )

            if not participant:
                return 0

            last_read_at = participant["last_read_at"]

            # Count messages after last_read_at
            if last_read_at:
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM messages
                    WHERE conversation_id = $1
                    AND created_at > $2
                    AND sender_id != $3
                    """,
                    conversation_id,
                    last_read_at,
                    user_id,
                )
            else:
                # Never read - count all messages from others
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM messages
                    WHERE conversation_id = $1
                    AND sender_id != $2
                    """,
                    conversation_id,
                    user_id,
                )

        return count or 0

    async def mark_read(
        self,
        conversation_id: UUID,
        user_id: UUID,
        message_id: UUID,
    ) -> None:
        """Mark messages as read up to a specific message."""
        pool = get_db_pool()

        async with pool.acquire() as conn:
            # Get the message's created_at timestamp
            message = await conn.fetchrow(
                """
                SELECT created_at FROM messages
                WHERE id = $1 AND conversation_id = $2
                """,
                message_id,
                conversation_id,
            )

            if not message:
                return

            # Update last_read_at for the participant
            await conn.execute(
                """
                UPDATE participants
                SET last_read_at = $1
                WHERE conversation_id = $2 AND user_id = $3
                AND (last_read_at IS NULL OR last_read_at < $1)
                """,
                message["created_at"],
                conversation_id,
                user_id,
            )

            logger.info(
                f"User {user_id} marked read in {conversation_id} up to {message_id}"
            )

    async def search_conversations(
        self,
        user_id: UUID,
        query: str,
        limit: int = 20,
    ) -> list[Conversation]:
        """Search conversations by name or message content."""
        pool = get_db_pool()
        search_pattern = f"%{query}%"

        async with pool.acquire() as conn:
            # Search by conversation name or message content
            rows = await conn.fetch(
                """
                SELECT DISTINCT c.id, c.name, c.type, c.created_at, c.updated_at
                FROM conversations c
                INNER JOIN participants p ON p.conversation_id = c.id
                LEFT JOIN messages m ON m.conversation_id = c.id
                WHERE p.user_id = $1
                AND (c.name ILIKE $2 OR m.content ILIKE $2)
                ORDER BY c.updated_at DESC
                LIMIT $3
                """,
                user_id,
                search_pattern,
                limit,
            )

        return [
            Conversation(
                id=row["id"],
                name=row["name"],
                type=ConversationType(row["type"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    async def update_conversation_timestamp(
        self,
        conversation_id: UUID,
    ) -> None:
        """Update conversation's updated_at timestamp."""
        pool = get_db_pool()
        now = datetime.now(timezone.utc)

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE conversations SET updated_at = $1 WHERE id = $2
                """,
                now,
                conversation_id,
            )


# Singleton instance
conversation_service = ConversationService()

