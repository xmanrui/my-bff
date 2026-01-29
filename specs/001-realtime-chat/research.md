# Research: Real-time Chat System

**Feature**: 001-realtime-chat
**Date**: 2026-01-29

## Technology Decisions

### 1. WebSocket Framework

**Decision**: FastAPI with native WebSocket support

**Rationale**:
- FastAPI provides built-in WebSocket support via Starlette
- Async-first design aligns with real-time requirements
- Single framework for both REST (history API) and WebSocket (real-time)
- Excellent performance characteristics for concurrent connections
- Strong typing with Pydantic for message validation

**Alternatives Considered**:
- **Socket.IO (python-socketio)**: More features (rooms, namespaces) but adds complexity; overkill for 1:1 chat
- **Channels (Django)**: Heavier framework, better for Django projects
- **aiohttp**: Lower-level, requires more boilerplate

### 2. PostgreSQL Schema Design

**Decision**: Normalized schema with conversation-centric design

**Rationale**:
- Conversations as first-class entities enable future group chat
- Messages indexed by (conversation_id, created_at) for efficient history queries
- Separate participants table supports flexible membership
- UUID primary keys for distributed-friendly IDs

**Alternatives Considered**:
- **Denormalized (messages with user arrays)**: Faster reads but complex updates
- **Time-series optimized**: Premature for current scale requirements

### 3. Redis Usage Pattern

**Decision**: Redis for presence + pub/sub message fan-out

**Rationale**:
- Presence data is ephemeral; Redis TTL handles automatic cleanup
- Pub/sub enables horizontal scaling (multiple server instances)
- Hash structures for presence: `presence:{user_id}` → {status, last_seen}
- Channel per conversation: `chat:{conversation_id}` for message broadcast

**Alternatives Considered**:
- **PostgreSQL LISTEN/NOTIFY**: Simpler but doesn't scale horizontally
- **RabbitMQ/Kafka**: Overkill for presence; adds operational complexity

### 4. Connection Management

**Decision**: Connection manager pattern with Redis-backed state

**Rationale**:
- In-memory dict tracks local WebSocket connections per server instance
- Redis pub/sub broadcasts messages to all server instances
- Heartbeat mechanism (30s interval) detects stale connections
- Graceful disconnect updates presence immediately

**Key Patterns**:
```
Client connects → Register in local manager → Subscribe to Redis channels
Message sent → Persist to PostgreSQL → Publish to Redis → Fan out to connections
Client disconnects → Unregister → Update presence → Unsubscribe
```

### 5. Message Delivery Guarantees

**Decision**: At-least-once delivery with client-side deduplication

**Rationale**:
- Messages persisted to PostgreSQL before acknowledgment (durability)
- Redis pub/sub for real-time delivery (best-effort)
- Client reconnection fetches missed messages from history API
- Message UUIDs enable client-side deduplication

### 6. Rate Limiting Strategy

**Decision**: Token bucket algorithm via Redis

**Rationale**:
- Redis INCR with TTL implements sliding window
- 30 messages/minute limit (FR-018) enforced server-side
- Returns 429 with retry-after header when exceeded
- Per-user tracking: `ratelimit:{user_id}:messages`

## Best Practices Applied

### WebSocket Best Practices
- Use binary frames for efficiency (JSON text for simplicity initially)
- Implement ping/pong for connection health
- Handle reconnection gracefully (exponential backoff on client)
- Close connections cleanly with appropriate status codes

### PostgreSQL Best Practices
- Connection pooling via asyncpg (min=5, max=20)
- Prepared statements for frequent queries
- Indexes on (conversation_id, created_at DESC) for history
- Partial index on unread messages for notification queries

### Redis Best Practices
- Connection pooling (redis-py async)
- Use HSET/HGET for presence (atomic operations)
- Set appropriate TTLs (presence: 5 minutes, auto-expire offline)
- Pub/sub pattern matching for efficient subscription

## Resolved Clarifications

All technical context items resolved:
- Language: Python 3.11+ (async support, performance)
- Framework: FastAPI (WebSocket + REST unified)
- Database: PostgreSQL with asyncpg
- Cache/Pub-sub: Redis with redis-py async
- Testing: pytest-asyncio for async test support
