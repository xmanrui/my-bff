"""WebSocket connection handler."""

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import ValidationError

from src.api.middleware.auth import validate_ws_token
from src.models.websocket import (
    WSMessageType,
    WSMessage,
    SendMessagePayload,
    MarkReadPayload,
    TypingPayload,
    TypingIndicatorPayload,
    ErrorPayload,
)
from src.services.conversation import conversation_service
from src.services.chat import chat_service
from src.services.presence import presence_service
from src.redis.pubsub import pubsub_manager, get_conversation_channel, get_presence_channel
from src.api.middleware.errors import RateLimitError, UnauthorizedError

logger = logging.getLogger("chat.websocket")

router = APIRouter()

# WebSocket close codes
WS_CLOSE_AUTH_FAILED = 4001
WS_CLOSE_TOKEN_EXPIRED = 4002
WS_CLOSE_CONNECTION_REPLACED = 4003
WS_CLOSE_SERVER_SHUTDOWN = 4004

HEARTBEAT_INTERVAL = 30
HEARTBEAT_TIMEOUT = 60


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        # user_id -> WebSocket
        self._connections: dict[UUID, WebSocket] = {}
        # user_id -> set of conversation_ids
        self._subscriptions: dict[UUID, set[UUID]] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        """Register a new connection."""
        # Close existing connection if any (connection replaced)
        if user_id in self._connections:
            old_ws = self._connections[user_id]
            try:
                await old_ws.close(code=WS_CLOSE_CONNECTION_REPLACED)
            except Exception:
                pass

        self._connections[user_id] = websocket
        self._subscriptions[user_id] = set()
        logger.info(f"User {user_id} connected")

    async def disconnect(self, user_id: UUID) -> None:
        """Remove a connection."""
        if user_id in self._connections:
            del self._connections[user_id]
        if user_id in self._subscriptions:
            # Unsubscribe from all channels
            for conv_id in self._subscriptions[user_id]:
                channel = get_conversation_channel(conv_id)
                callback = self._get_callback(user_id)
                await pubsub_manager.unsubscribe(channel, callback)
            del self._subscriptions[user_id]
        logger.info(f"User {user_id} disconnected")

    async def subscribe_to_conversation(
        self, user_id: UUID, conversation_id: UUID
    ) -> None:
        """Subscribe user to conversation messages."""
        if user_id not in self._subscriptions:
            return
        if conversation_id in self._subscriptions[user_id]:
            return

        channel = get_conversation_channel(conversation_id)
        callback = self._get_callback(user_id)
        await pubsub_manager.subscribe(channel, callback)
        self._subscriptions[user_id].add(conversation_id)

    def _get_callback(self, user_id: UUID):
        """Get callback for pub/sub messages."""
        async def callback(data: dict) -> None:
            await self.send_to_user(user_id, data)
        return callback

    async def send_to_user(self, user_id: UUID, data: dict) -> None:
        """Send message to a specific user."""
        if user_id in self._connections:
            try:
                await self._connections[user_id].send_json(data)
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")

    async def broadcast_to_conversation(
        self, conversation_id: UUID, data: dict, exclude_user: UUID | None = None
    ) -> None:
        """Broadcast message to all users in a conversation."""
        channel = get_conversation_channel(conversation_id)
        await pubsub_manager.publish(channel, data)

    def get_connection(self, user_id: UUID) -> WebSocket | None:
        """Get WebSocket connection for a user."""
        return self._connections.get(user_id)

    def is_connected(self, user_id: UUID) -> bool:
        """Check if user is connected."""
        return user_id in self._connections


# Global connection manager
connection_manager = ConnectionManager()


async def send_error(
    websocket: WebSocket,
    code: str,
    message: str,
    original_type: str | None = None,
) -> None:
    """Send error message to client."""
    payload = ErrorPayload(
        code=code, message=message, original_type=original_type
    )
    await websocket.send_json({
        "type": WSMessageType.ERROR.value,
        "payload": payload.model_dump(by_alias=True),
    })


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """WebSocket endpoint for real-time chat."""
    # Validate token
    user_id = validate_ws_token(token)
    if not user_id:
        await websocket.close(code=WS_CLOSE_AUTH_FAILED)
        return

    await websocket.accept()
    await connection_manager.connect(user_id, websocket)

    # Set user as online
    socket_id = str(id(websocket))
    await presence_service.set_online(user_id, socket_id)

    # Subscribe to presence updates
    presence_channel = get_presence_channel()
    await pubsub_manager.subscribe(
        presence_channel,
        connection_manager._get_callback(user_id),
    )

    # Start heartbeat task
    heartbeat_task = asyncio.create_task(heartbeat_handler(websocket, user_id))

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")
                payload = message.get("payload", {})

                await handle_message(websocket, user_id, msg_type, payload)

            except json.JSONDecodeError:
                await send_error(websocket, "invalid_payload", "Invalid JSON")
            except ValidationError as e:
                await send_error(
                    websocket, "invalid_payload", str(e), msg_type
                )

    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected")
    except Exception as e:
        logger.exception(f"WebSocket error for user {user_id}: {e}")
    finally:
        heartbeat_task.cancel()
        # Set user as offline
        await presence_service.set_offline(user_id)
        # Unsubscribe from presence channel
        await pubsub_manager.unsubscribe(
            get_presence_channel(),
            connection_manager._get_callback(user_id),
        )
        await connection_manager.disconnect(user_id)


async def handle_message(
    websocket: WebSocket,
    user_id: UUID,
    msg_type: str,
    payload: dict,
) -> None:
    """Handle incoming WebSocket message."""
    if msg_type == WSMessageType.SEND_MESSAGE.value:
        await handle_send_message(websocket, user_id, payload)
    elif msg_type == WSMessageType.MARK_READ.value:
        await handle_mark_read(websocket, user_id, payload)
    elif msg_type == WSMessageType.TYPING_START.value:
        await handle_typing(websocket, user_id, payload, is_typing=True)
    elif msg_type == WSMessageType.TYPING_STOP.value:
        await handle_typing(websocket, user_id, payload, is_typing=False)
    elif msg_type == "ping":
        await websocket.send_json({"type": "pong"})
    else:
        await send_error(
            websocket, "invalid_payload", f"Unknown message type: {msg_type}"
        )


async def handle_send_message(
    websocket: WebSocket,
    user_id: UUID,
    payload: dict,
) -> None:
    """Handle send_message from client."""
    try:
        data = SendMessagePayload(**payload)

        # Subscribe to conversation if not already
        await connection_manager.subscribe_to_conversation(
            user_id, data.conversation_id
        )

        # Send message
        message = await chat_service.send_message(
            user_id=user_id,
            conversation_id=data.conversation_id,
            content=data.content,
            client_message_id=data.client_message_id,
        )

        # Send status confirmation to sender
        await websocket.send_json({
            "type": WSMessageType.MESSAGE_STATUS.value,
            "payload": {
                "messageId": str(message.id),
                "status": message.status.value,
                "clientMessageId": str(data.client_message_id),
            },
        })

    except RateLimitError as e:
        await send_error(
            websocket,
            "rate_limited",
            e.message,
            WSMessageType.SEND_MESSAGE.value,
        )
    except UnauthorizedError as e:
        await send_error(
            websocket,
            "invalid_conversation",
            e.message,
            WSMessageType.SEND_MESSAGE.value,
        )
    except ValidationError as e:
        await send_error(
            websocket,
            "invalid_payload",
            str(e),
            WSMessageType.SEND_MESSAGE.value,
        )


async def handle_mark_read(
    websocket: WebSocket,
    user_id: UUID,
    payload: dict,
) -> None:
    """Handle mark_read from client."""
    try:
        data = MarkReadPayload(**payload)
        await conversation_service.mark_read(
            conversation_id=data.conversation_id,
            user_id=user_id,
            message_id=data.message_id,
        )
    except ValidationError as e:
        await send_error(
            websocket,
            "invalid_payload",
            str(e),
            WSMessageType.MARK_READ.value,
        )


async def handle_typing(
    websocket: WebSocket,
    user_id: UUID,
    payload: dict,
    is_typing: bool,
) -> None:
    """Handle typing_start/typing_stop from client."""
    try:
        data = TypingPayload(**payload)

        # Broadcast typing indicator to conversation
        indicator = TypingIndicatorPayload(
            conversation_id=data.conversation_id,
            user_id=user_id,
            is_typing=is_typing,
        )
        channel = get_conversation_channel(data.conversation_id)
        await pubsub_manager.publish(
            channel,
            {
                "type": WSMessageType.TYPING_INDICATOR.value,
                "payload": indicator.model_dump(by_alias=True, mode="json"),
            },
        )
    except ValidationError as e:
        msg_type = (
            WSMessageType.TYPING_START.value
            if is_typing
            else WSMessageType.TYPING_STOP.value
        )
        await send_error(websocket, "invalid_payload", str(e), msg_type)


async def heartbeat_handler(websocket: WebSocket, user_id: UUID) -> None:
    """Send periodic heartbeat pings and refresh presence."""
    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            try:
                await websocket.send_json({"type": "ping"})
                # Refresh presence TTL on each heartbeat
                await presence_service.refresh_presence(user_id)
            except Exception:
                break
    except asyncio.CancelledError:
        pass
