"""Chat service for message sending and receiving."""

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.db.connection import get_connection
from src.redis.connection import get_redis
from src.redis.pubsub import pubsub_manager, get_conversation_channel
from src.models.message import Message, MessageStatus
from src.models.websocket import (
    WSMessageType,
    MessageReceivedPayload,
    MessageStatusPayload,
)
from src.api.middleware.errors import RateLimitError, UnauthorizedError

logger = logging.getLogger("chat.services.chat")

RATE_LIMIT_KEY = "ratelimit:{user_id}:messages"
RATE_LIMIT_MAX = 30
RATE_LIMIT_WINDOW = 60  # seconds
MAX_RETRIES = 3


class ChatService:
    """Service for chat message operations."""

    async def check_rate_limit(self, user_id: UUID) -> None:
        """Check if user has exceeded rate limit."""
        redis = get_redis()
        key = RATE_LIMIT_KEY.format(user_id=user_id)

        count = await redis.get(key)
        if count and int(count) >= RATE_LIMIT_MAX:
            ttl = await redis.ttl(key)
            raise RateLimitError(retry_after=max(ttl, 1))

    async def increment_rate_limit(self, user_id: UUID) -> None:
        """Increment rate limit counter."""
        redis = get_redis()
        key = RATE_LIMIT_KEY.format(user_id=user_id)

        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, RATE_LIMIT_WINDOW)
        await pipe.execute()

    async def verify_participant(
        self, user_id: UUID, conversation_id: UUID
    ) -> bool:
        """Verify user is a participant in the conversation."""
        async with get_connection() as conn:
            result = await conn.fetchval(
                """
                SELECT 1 FROM participants
                WHERE user_id = $1 AND conversation_id = $2
                """,
                user_id,
                conversation_id,
            )
            return result is not None

    async def send_message(
        self,
        user_id: UUID,
        conversation_id: UUID,
        content: str,
        client_message_id: UUID,
    ) -> Message:
        """Send a message to a conversation."""
        # Check rate limit
        await self.check_rate_limit(user_id)

        # Verify user is participant
        if not await self.verify_participant(user_id, conversation_id):
            raise UnauthorizedError("Not a participant in this conversation")

        # Increment rate limit
        await self.increment_rate_limit(user_id)

        # Persist message
        message = await self._persist_message(
            user_id, conversation_id, content
        )

        # Update conversation timestamp
        await self._update_conversation_timestamp(conversation_id)

        # Broadcast via pub/sub
        await self._broadcast_message(message, client_message_id)

        logger.info(
            f"Message sent: {message.id} in conversation {conversation_id}"
        )
        return message

    async def _persist_message(
        self,
        sender_id: UUID,
        conversation_id: UUID,
        content: str,
    ) -> Message:
        """Persist message to database."""
        async with get_connection() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO messages (conversation_id, sender_id, content, status)
                VALUES ($1, $2, $3, 'sent')
                RETURNING id, conversation_id, sender_id, content, created_at, status
                """,
                conversation_id,
                sender_id,
                content,
            )
            return Message(
                id=row["id"],
                conversation_id=row["conversation_id"],
                sender_id=row["sender_id"],
                content=row["content"],
                created_at=row["created_at"],
                status=MessageStatus(row["status"]),
            )

    async def _update_conversation_timestamp(
        self, conversation_id: UUID
    ) -> None:
        """Update conversation's updated_at timestamp."""
        async with get_connection() as conn:
            await conn.execute(
                """
                UPDATE conversations SET updated_at = NOW()
                WHERE id = $1
                """,
                conversation_id,
            )

    async def _broadcast_message(
        self, message: Message, client_message_id: UUID
    ) -> None:
        """Broadcast message via Redis pub/sub."""
        channel = get_conversation_channel(message.conversation_id)
        payload = MessageReceivedPayload(
            id=message.id,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            content=message.content,
            created_at=message.created_at,
            status=message.status.value,
        )
        await pubsub_manager.publish(
            channel,
            {
                "type": WSMessageType.MESSAGE_RECEIVED.value,
                "payload": payload.model_dump(by_alias=True, mode="json"),
                "client_message_id": str(client_message_id),
            },
        )

    async def update_message_status(
        self,
        message_id: UUID,
        status: MessageStatus,
        client_message_id: UUID | None = None,
    ) -> None:
        """Update message delivery status."""
        async with get_connection() as conn:
            row = await conn.fetchrow(
                """
                UPDATE messages SET status = $1
                WHERE id = $2
                RETURNING conversation_id
                """,
                status.value,
                message_id,
            )
            if row and client_message_id:
                channel = get_conversation_channel(row["conversation_id"])
                payload = MessageStatusPayload(
                    message_id=message_id,
                    status=status.value,
                    client_message_id=client_message_id,
                )
                await pubsub_manager.publish(
                    channel,
                    {
                        "type": WSMessageType.MESSAGE_STATUS.value,
                        "payload": payload.model_dump(by_alias=True, mode="json"),
                    },
                )

    async def send_with_retry(
        self,
        user_id: UUID,
        conversation_id: UUID,
        content: str,
        client_message_id: UUID,
        max_retries: int = MAX_RETRIES,
    ) -> Message | None:
        """Send message with retry logic."""
        for attempt in range(max_retries):
            try:
                return await self.send_message(
                    user_id, conversation_id, content, client_message_id
                )
            except RateLimitError:
                raise  # Don't retry rate limits
            except Exception as e:
                logger.warning(
                    f"Message send attempt {attempt + 1} failed: {e}"
                )
                if attempt == max_retries - 1:
                    logger.error(
                        f"Message send failed after {max_retries} attempts"
                    )
                    return None
        return None


# Singleton instance
chat_service = ChatService()
