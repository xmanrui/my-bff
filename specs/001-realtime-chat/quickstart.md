# Quickstart: Real-time Chat System

**Feature**: 001-realtime-chat
**Date**: 2026-01-29

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Docker (optional, for local services)

## Local Development Setup

### 1. Start Infrastructure

```bash
# Using Docker Compose (recommended)
docker compose up -d postgres redis

# Or manually:
# PostgreSQL on localhost:5432
# Redis on localhost:6379
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Required variables:
# DATABASE_URL=postgresql://user:pass@localhost:5432/chat
# REDIS_URL=redis://localhost:6379/0
# JWT_SECRET=your-secret-key
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Start the Server

```bash
# Development mode with auto-reload
uvicorn src.api.main:app --reload --port 8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/conversations` | List conversations |
| POST | `/api/v1/conversations` | Create conversation |
| GET | `/api/v1/conversations/{id}` | Get conversation |
| GET | `/api/v1/conversations/{id}/messages` | Get message history |
| POST | `/api/v1/conversations/{id}/messages` | Send message (REST) |
| GET | `/api/v1/conversations/search?q=` | Search messages |
| GET | `/api/v1/users/{id}/presence` | Get user presence |
| WS | `/api/v1/ws?token=` | WebSocket connection |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_chat_service.py

# Run integration tests (requires running services)
pytest tests/integration/
```

## WebSocket Quick Test

```python
import asyncio
import websockets
import json

async def test_chat():
    uri = "ws://localhost:8000/api/v1/ws?token=YOUR_TOKEN"
    async with websockets.connect(uri) as ws:
        # Send a message
        await ws.send(json.dumps({
            "type": "send_message",
            "payload": {
                "conversationId": "conv-uuid",
                "content": "Hello!",
                "clientMessageId": "client-uuid"
            }
        }))

        # Receive response
        response = await ws.recv()
        print(json.loads(response))

asyncio.run(test_chat())
```

## Key Files

| File | Purpose |
|------|---------|
| `src/api/main.py` | FastAPI application entry |
| `src/api/routes/websocket.py` | WebSocket handler |
| `src/services/chat.py` | Message business logic |
| `src/services/presence.py` | Presence tracking |
| `src/db/connection.py` | PostgreSQL pool |
| `src/redis/pubsub.py` | Redis pub/sub |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `REDIS_URL` | Yes | - | Redis connection string |
| `JWT_SECRET` | Yes | - | Secret for JWT validation |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `WS_HEARTBEAT_INTERVAL` | No | `30` | WebSocket ping interval (seconds) |
| `RATE_LIMIT_MESSAGES` | No | `30` | Max messages per minute |
