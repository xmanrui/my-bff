# Implementation Plan: Real-time Chat System

**Branch**: `001-realtime-chat` | **Date**: 2026-01-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-realtime-chat/spec.md`

## Summary

Build a real-time chat system enabling instant messaging between users with persistent message history and live presence indicators. Technical approach: WebSocket connections for real-time message delivery, PostgreSQL for durable message storage and history retrieval, Redis for ephemeral presence state and pub/sub message broadcasting.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI (HTTP/WebSocket), asyncpg (PostgreSQL), redis-py (Redis), Pydantic (validation)
**Storage**: PostgreSQL (messages, conversations, users), Redis (presence, pub/sub)
**Testing**: pytest, pytest-asyncio, httpx (async test client)
**Target Platform**: Linux server (containerized)
**Project Type**: Web application (backend API + WebSocket server)
**Performance Goals**: 1,000 concurrent WebSocket connections, <1s message delivery (SC-001)
**Constraints**: <200ms p95 for message history queries, <5s presence update propagation
**Scale/Scope**: 1,000 concurrent users (SC-005), indefinite message retention (FR-009)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution is in template state (not yet configured for this project). Proceeding with standard best practices:

- [x] **Testability**: All components designed for unit and integration testing
- [x] **Simplicity**: Minimal dependencies, standard patterns (REST + WebSocket)
- [x] **Observability**: Structured logging, connection metrics planned

## Project Structure

### Documentation (this feature)

```text
specs/001-realtime-chat/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI spec)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── conversations.py # REST endpoints for conversations
│   │   ├── messages.py      # REST endpoints for message history
│   │   └── websocket.py     # WebSocket connection handler
│   └── dependencies.py      # Dependency injection (DB, Redis)
├── models/
│   ├── __init__.py
│   ├── conversation.py      # Conversation entity
│   ├── message.py           # Message entity
│   └── presence.py          # Presence entity
├── services/
│   ├── __init__.py
│   ├── chat.py              # Message sending/receiving logic
│   ├── presence.py          # Presence tracking logic
│   └── history.py           # Message history retrieval
├── db/
│   ├── __init__.py
│   ├── connection.py        # PostgreSQL connection pool
│   └── migrations/          # Database migrations (Alembic)
└── redis/
    ├── __init__.py
    ├── connection.py        # Redis connection
    └── pubsub.py            # Pub/sub for message broadcasting

tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_chat_service.py
│   ├── test_presence_service.py
│   └── test_history_service.py
├── integration/
│   ├── test_websocket.py
│   ├── test_message_flow.py
│   └── test_presence_updates.py
└── contract/
    └── test_api_contracts.py
```

**Structure Decision**: Single backend application with clear separation between API layer (routes), business logic (services), and data access (db, redis). WebSocket and REST endpoints coexist in the same FastAPI application.
