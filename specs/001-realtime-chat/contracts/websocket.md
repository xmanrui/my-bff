# WebSocket Contract: Real-time Chat

**Endpoint**: `ws://host/api/v1/ws`

## Connection

### Authentication
- Connect with auth token in query param: `?token={jwt}`
- Server validates token and associates connection with user
- Invalid token: close with code 4001

### Heartbeat
- Client sends `ping` every 30 seconds
- Server responds with `pong`
- No ping for 60s: server closes connection

## Message Types

### Client → Server

#### send_message
Send a new message to a conversation.
```json
{
  "type": "send_message",
  "payload": {
    "conversationId": "uuid",
    "content": "string (1-10000 chars)",
    "clientMessageId": "uuid (for deduplication)"
  }
}
```

#### typing_start
Indicate user started typing.
```json
{
  "type": "typing_start",
  "payload": {
    "conversationId": "uuid"
  }
}
```

#### typing_stop
Indicate user stopped typing.
```json
{
  "type": "typing_stop",
  "payload": {
    "conversationId": "uuid"
  }
}
```

#### mark_read
Mark messages as read up to a timestamp.
```json
{
  "type": "mark_read",
  "payload": {
    "conversationId": "uuid",
    "messageId": "uuid"
  }
}
```

### Server → Client

#### message_received
New message in a conversation.
```json
{
  "type": "message_received",
  "payload": {
    "id": "uuid",
    "conversationId": "uuid",
    "senderId": "uuid",
    "content": "string",
    "createdAt": "ISO8601",
    "status": "sent"
  }
}
```

#### message_status
Update on message delivery status.
```json
{
  "type": "message_status",
  "payload": {
    "messageId": "uuid",
    "status": "sent | delivered | failed",
    "clientMessageId": "uuid (echoed back)"
  }
}
```

#### typing_indicator
Someone is typing in a conversation.
```json
{
  "type": "typing_indicator",
  "payload": {
    "conversationId": "uuid",
    "userId": "uuid",
    "isTyping": true
  }
}
```

#### presence_update
User presence changed.
```json
{
  "type": "presence_update",
  "payload": {
    "userId": "uuid",
    "status": "online | away | offline",
    "lastSeen": "ISO8601 (if offline)"
  }
}
```

#### error
Error response.
```json
{
  "type": "error",
  "payload": {
    "code": "string",
    "message": "string",
    "originalType": "string (the message type that caused error)"
  }
}
```

## Error Codes

| Code | Description |
|------|-------------|
| `rate_limited` | Too many messages (30/min exceeded) |
| `invalid_conversation` | User not a participant |
| `message_too_long` | Content exceeds 10,000 chars |
| `invalid_payload` | Malformed message |

## Close Codes

| Code | Description |
|------|-------------|
| 4001 | Authentication failed |
| 4002 | Token expired |
| 4003 | Connection replaced (user connected elsewhere) |
| 4004 | Server shutdown |
