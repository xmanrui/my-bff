"""Redis pub/sub manager for message broadcasting."""

import asyncio
import json
from typing import Any, Callable, Coroutine
from uuid import UUID

from src.redis.connection import get_redis


class PubSubManager:
    """Manages Redis pub/sub subscriptions and message broadcasting."""

    def __init__(self):
        self._pubsub = None
        self._subscriptions: dict[str, set[Callable]] = {}
        self._listener_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the pub/sub listener."""
        redis_client = get_redis()
        self._pubsub = redis_client.pubsub()
        self._listener_task = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        """Stop the pub/sub listener."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.close()

    async def subscribe(
        self,
        channel: str,
        callback: Callable[[dict], Coroutine[Any, Any, None]],
    ) -> None:
        """Subscribe to a channel with a callback."""
        if channel not in self._subscriptions:
            self._subscriptions[channel] = set()
            if self._pubsub:
                await self._pubsub.subscribe(channel)
        self._subscriptions[channel].add(callback)

    async def unsubscribe(
        self,
        channel: str,
        callback: Callable[[dict], Coroutine[Any, Any, None]],
    ) -> None:
        """Unsubscribe a callback from a channel."""
        if channel in self._subscriptions:
            self._subscriptions[channel].discard(callback)
            if not self._subscriptions[channel]:
                del self._subscriptions[channel]
                if self._pubsub:
                    await self._pubsub.unsubscribe(channel)

    async def publish(self, channel: str, message: dict) -> None:
        """Publish a message to a channel."""
        redis_client = get_redis()
        await redis_client.publish(channel, json.dumps(message, default=str))

    async def _listen(self) -> None:
        """Listen for messages on subscribed channels."""
        if not self._pubsub:
            return

        async for message in self._pubsub.listen():
            if message["type"] == "message":
                channel = message["channel"]
                if channel in self._subscriptions:
                    try:
                        data = json.loads(message["data"])
                    except json.JSONDecodeError:
                        continue

                    for callback in self._subscriptions[channel]:
                        try:
                            await callback(data)
                        except Exception:
                            pass  # Log in production


def get_conversation_channel(conversation_id: UUID) -> str:
    """Get the Redis channel name for a conversation."""
    return f"chat:{conversation_id}"


def get_presence_channel() -> str:
    """Get the Redis channel name for presence updates."""
    return "presence:updates"


# Global pub/sub manager instance
pubsub_manager = PubSubManager()
