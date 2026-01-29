# Data Model: Real-time Chat System

**Feature**: 001-realtime-chat
**Date**: 2026-01-29

## Entity Relationship Diagram

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────┐
│    User     │       │   Conversation   │       │   Message   │
├─────────────┤       ├──────────────────┤       ├─────────────┤
│ id (PK)     │──┐    │ id (PK)          │──┐    │ id (PK)     │
│ display_name│  │    │ created_at       │  │    │ conv_id(FK) │──┐
│ avatar_url  │  │    │ updated_at       │  │    │ sender_id   │  │
│ created_at  │  │    └──────────────────┘  │    │ content     │  │
└─────────────┘  │                          │    │ created_at  │  │
                │    ┌──────────────────┐   │    │ status      │  │
                │    │   Participant    │   │    └─────────────┘  │
                │    ├──────────────────┤   │                     │
                └───▶│ user_id (FK)     │   │                     │
                     │ conv_id (FK)     │◀──┴─────────────────────┘
                     │ joined_at        │
                     │ last_read_at     │
                     └──────────────────┘
```

## PostgreSQL Entities

### User

Represents a person who can participate in conversations.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| display_name | VARCHAR(100) | NOT NULL | User's display name |
| avatar_url | VARCHAR(500) | NULL | Profile image URL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Account creation time |

**Notes**: User authentication handled externally; this table stores chat-specific profile data.

### Conversation

A communication channel between participants.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Conversation start time |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Last activity time |

**Indexes**:
- `idx_conversation_updated_at` on (updated_at DESC) - for sorting by recent activity

### Participant

Links users to conversations (junction table).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| user_id | UUID | PK, FK → User.id | Participant user |
| conversation_id | UUID | PK, FK → Conversation.id | Conversation joined |
| joined_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | When user joined |
| last_read_at | TIMESTAMPTZ | NULL | Last message read timestamp |

**Indexes**:
- `idx_participant_user_id` on (user_id) - for listing user's conversations
- `idx_participant_conv_id` on (conversation_id) - for listing conversation members

**Constraints**:
- Composite PK on (user_id, conversation_id)

### Message

A text message sent within a conversation.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| conversation_id | UUID | NOT NULL, FK → Conversation.id | Parent conversation |
| sender_id | UUID | NOT NULL, FK → User.id | Message author |
| content | TEXT | NOT NULL, CHECK(length <= 10000) | Message text (FR-003) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Send timestamp |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'sent' | Delivery status |

**Status Values**: `sending`, `sent`, `delivered`, `failed`

**Indexes**:
- `idx_message_conv_created` on (conversation_id, created_at DESC) - for history pagination
- `idx_message_sender` on (sender_id) - for user's sent messages

**Validation Rules**:
- content length: 1-10,000 characters (FR-003)
- status must be one of: sending, sent, delivered, failed

## Redis Entities

### Presence

Ephemeral user presence state stored in Redis.

**Key Pattern**: `presence:{user_id}`

| Field | Type | Description |
|-------|------|-------------|
| status | string | `online`, `away`, `offline` |
| last_seen | ISO timestamp | Last activity time |
| socket_id | string | Current WebSocket connection ID |

**TTL**: 300 seconds (5 minutes) - auto-expires to offline

**Operations**:
- HSET on connect/activity
- HGET for presence lookup
- EXPIRE refresh on heartbeat

### Rate Limit

Per-user message rate limiting.

**Key Pattern**: `ratelimit:{user_id}:messages`

| Field | Type | Description |
|-------|------|-------------|
| count | integer | Messages sent in window |

**TTL**: 60 seconds (sliding window)

**Operations**:
- INCR on message send
- GET to check limit (30/minute per FR-018)

### Pub/Sub Channels

**Conversation Channel**: `chat:{conversation_id}`
- Published: New messages, typing indicators
- Subscribers: All connected participants

**Presence Channel**: `presence:updates`
- Published: User status changes
- Subscribers: All connected clients

## State Transitions

### Message Status

```
┌──────────┐    persist    ┌──────┐    deliver    ┌───────────┐
│ sending  │──────────────▶│ sent │──────────────▶│ delivered │
└──────────┘               └──────┘               └───────────┘
     │                          │
     │ error                    │ error (after retries)
     ▼                          ▼
┌──────────┐               ┌──────────┐
│  failed  │◀──────────────│  failed  │
└──────────┘               └──────────┘
```

### Presence Status

```
┌─────────┐    connect    ┌────────┐    5min idle    ┌──────┐
│ offline │──────────────▶│ online │────────────────▶│ away │
└─────────┘               └────────┘                 └──────┘
     ▲                         │                         │
     │                         │ disconnect              │ disconnect
     │                         ▼                         │
     └─────────────────────────┴─────────────────────────┘
```
