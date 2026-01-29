"""Presence service for user status tracking."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from src.redis.connection import get_redis
from src.redis.pubsub import pubsub_manager, get_presence_channel
from src.models.presence import Presence, PresenceStatus, PresenceUpdate
from src.models.websocket import WSMessageType, PresenceUpdatePayload

logger = logging.getLogger("chat.services.presence")

PRESENCE_KEY = "presence:{user_id}"
PRESENCE_TTL = 300  # 5 minutes
AWAY_THRESHOLD = 300  # 5 minutes of inactivity


class PresenceService:
    """Service for user presence operations."""

    async def update_status(
        self,
        user_id: UUID,
        status: PresenceStatus,
        socket_id: str | None = None,
    ) -> None:
        """Update user presence status."""
        redis = get_redis()
        key = PRESENCE_KEY.format(user_id=user_id)
        now = datetime.now(timezone.utc)

        data = {
            "status": status.value,
            "last_seen": now.isoformat(),
        }
        if socket_id:
            data["socket_id"] = socket_id

        await redis.hset(key, mapping=data)

        # Set TTL for auto-expire to offline
        if status != PresenceStatus.OFFLINE:
            await redis.expire(key, PRESENCE_TTL)

        # Broadcast presence update
        await self._broadcast_presence_update(user_id, status, now)

        logger.info(f"User {user_id} status updated to {status.value}")

    async def get_presence(self, user_id: UUID) -> Presence:
        """Get user presence status."""
        redis = get_redis()
        key = PRESENCE_KEY.format(user_id=user_id)

        data = await redis.hgetall(key)

        if not data:
            return Presence(status=PresenceStatus.OFFLINE)

        status = PresenceStatus(data.get("status", "offline"))
        last_seen_str = data.get("last_seen")
        last_seen = None
        if last_seen_str:
            last_seen = datetime.fromisoformat(last_seen_str)

        # Check for away status based on inactivity
        if status == PresenceStatus.ONLINE and last_seen:
            elapsed = (datetime.now(timezone.utc) - last_seen).total_seconds()
            if elapsed >= AWAY_THRESHOLD:
                status = PresenceStatus.AWAY

        return Presence(
            status=status,
            last_seen=last_seen if status == PresenceStatus.OFFLINE else None,
        )

    async def refresh_presence(self, user_id: UUID) -> None:
        """Refresh presence TTL on activity (heartbeat)."""
        redis = get_redis()
        key = PRESENCE_KEY.format(user_id=user_id)
        now = datetime.now(timezone.utc)

        # Update last_seen and refresh TTL
        await redis.hset(key, "last_seen", now.isoformat())
        await redis.expire(key, PRESENCE_TTL)

    async def set_online(self, user_id: UUID, socket_id: str) -> None:
        """Set user as online when they connect."""
        await self.update_status(user_id, PresenceStatus.ONLINE, socket_id)

    async def set_offline(self, user_id: UUID) -> None:
        """Set user as offline when they disconnect."""
        redis = get_redis()
        key = PRESENCE_KEY.format(user_id=user_id)
        now = datetime.now(timezone.utc)

        # Update status to offline with last_seen
        await redis.hset(key, mapping={
            "status": PresenceStatus.OFFLINE.value,
            "last_seen": now.isoformat(),
        })
        # Remove TTL so offline status persists
        await redis.persist(key)

        # Broadcast offline status
        await self._broadcast_presence_update(
            user_id, PresenceStatus.OFFLINE, now
        )

        logger.info(f"User {user_id} set to offline")

    async def _broadcast_presence_update(
        self,
        user_id: UUID,
        status: PresenceStatus,
        last_seen: datetime,
    ) -> None:
        """Broadcast presence update via pub/sub."""
        channel = get_presence_channel()
        payload = PresenceUpdatePayload(
            user_id=user_id,
            status=status.value,
            last_seen=last_seen if status == PresenceStatus.OFFLINE else None,
        )
        await pubsub_manager.publish(
            channel,
            {
                "type": WSMessageType.PRESENCE_UPDATE.value,
                "payload": payload.model_dump(by_alias=True, mode="json"),
            },
        )


# Singleton instance
presence_service = PresenceService()
