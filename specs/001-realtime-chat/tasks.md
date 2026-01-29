# Tasks: Real-time Chat System

**Input**: Design documents from `/specs/001-realtime-chat/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in specification. Test tasks omitted.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in descriptions

## Path Conventions

- **Project type**: Single backend application
- **Source**: `src/` at repository root
- **Tests**: `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure per plan.md layout
- [x] T002 Initialize Python project with pyproject.toml (FastAPI, asyncpg, redis-py, Pydantic)
- [x] T003 [P] Create requirements.txt with pinned dependencies
- [x] T004 [P] Configure ruff for linting in pyproject.toml
- [x] T005 [P] Create .env.example with DATABASE_URL, REDIS_URL, JWT_SECRET
- [x] T006 [P] Create docker-compose.yml for PostgreSQL and Redis local development

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Create PostgreSQL connection pool in src/db/connection.py
- [x] T008 Create Redis connection manager in src/redis/connection.py
- [x] T009 Setup Alembic migrations framework in src/db/migrations/
- [x] T010 Create initial migration with User, Conversation, Participant, Message tables in src/db/migrations/versions/
- [x] T011 [P] Create User Pydantic model in src/models/user.py
- [x] T012 [P] Create Conversation Pydantic model in src/models/conversation.py
- [x] T013 [P] Create Participant Pydantic model in src/models/participant.py
- [x] T014 [P] Create Message Pydantic model in src/models/message.py
- [x] T015 Create FastAPI app entry point in src/api/main.py
- [x] T016 Create dependency injection for DB and Redis in src/api/dependencies.py
- [x] T017 [P] Implement JWT token validation middleware in src/api/middleware/auth.py
- [x] T018 [P] Create base error handling and logging in src/api/middleware/errors.py
- [x] T019 Create Redis pub/sub manager in src/redis/pubsub.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Send and Receive Messages (Priority: P1) MVP

**Goal**: Enable real-time message exchange between users via WebSocket

**Independent Test**: Two users can exchange messages and see them appear instantly (<1s)

### Implementation for User Story 1

- [x] T020 [P] [US1] Create Presence Pydantic model in src/models/presence.py
- [x] T021 [P] [US1] Create WebSocket message schemas (send_message, message_received, message_status) in src/models/websocket.py
- [x] T022 [US1] Implement ChatService with send_message logic in src/services/chat.py
- [x] T023 [US1] Implement rate limiting (30 msg/min) using Redis in src/services/chat.py
- [x] T024 [US1] Implement message persistence to PostgreSQL in src/services/chat.py
- [x] T025 [US1] Implement WebSocket connection manager in src/api/routes/websocket.py
- [x] T026 [US1] Implement WebSocket authentication (token validation) in src/api/routes/websocket.py
- [x] T027 [US1] Implement send_message WebSocket handler in src/api/routes/websocket.py
- [x] T028 [US1] Implement Redis pub/sub for message broadcasting in src/api/routes/websocket.py
- [x] T029 [US1] Implement message_status updates (sent, delivered) in src/services/chat.py
- [x] T030 [US1] Implement heartbeat ping/pong handling in src/api/routes/websocket.py
- [x] T031 [US1] Add message retry logic (3 attempts) for failed deliveries in src/services/chat.py

**Checkpoint**: Users can send/receive real-time messages via WebSocket

---

## Phase 4: User Story 2 - View Message History (Priority: P2)

**Goal**: Load and paginate historical messages in conversations

**Independent Test**: Opening a conversation displays last 50 messages in chronological order

### Implementation for User Story 2

- [x] T032 [US2] Implement HistoryService with get_messages in src/services/history.py
- [x] T033 [US2] Implement cursor-based pagination for messages in src/services/history.py
- [x] T034 [US2] Create GET /conversations/{id}/messages endpoint in src/api/routes/messages.py
- [x] T035 [US2] Implement message ordering (chronological by created_at) in src/services/history.py
- [x] T036 [US2] Add index optimization for (conversation_id, created_at DESC) query in src/db/migrations/versions/

**Checkpoint**: Users can view and scroll through message history

---

## Phase 5: User Story 3 - See User Presence (Priority: P3)

**Goal**: Display real-time online/away/offline status for users

**Independent Test**: User status updates visible to others within 5 seconds of change

### Implementation for User Story 3

- [x] T037 [US3] Implement PresenceService with update_status in src/services/presence.py
- [x] T038 [US3] Implement Redis presence storage (HSET presence:{user_id}) in src/services/presence.py
- [x] T039 [US3] Implement presence TTL (5 min auto-expire to offline) in src/services/presence.py
- [x] T040 [US3] Implement away status detection (5 min inactivity) in src/services/presence.py
- [x] T041 [US3] Implement presence_update WebSocket broadcast in src/api/routes/websocket.py
- [x] T042 [US3] Create GET /users/{userId}/presence endpoint in src/api/routes/presence.py
- [x] T043 [US3] Update presence on WebSocket connect/disconnect in src/api/routes/websocket.py
- [x] T044 [US3] Implement last_seen timestamp tracking in src/services/presence.py

**Checkpoint**: Users can see real-time presence status of other users

---

## Phase 6: User Story 4 - Manage Conversations (Priority: P4)

**Goal**: Create, list, and organize conversations with unread indicators

**Independent Test**: User can create a conversation and see it in their list sorted by activity

### Implementation for User Story 4

- [x] T045 [P] [US4] Implement ConversationService with create_conversation in src/services/conversation.py
- [x] T046 [P] [US4] Implement get_user_conversations (sorted by updated_at) in src/services/conversation.py
- [x] T047 [US4] Create POST /conversations endpoint in src/api/routes/conversations.py
- [x] T048 [US4] Create GET /conversations endpoint with pagination in src/api/routes/conversations.py
- [x] T049 [US4] Create GET /conversations/{id} endpoint in src/api/routes/conversations.py
- [x] T050 [US4] Implement unread count calculation (last_read_at vs messages) in src/services/conversation.py
- [x] T051 [US4] Implement mark_read WebSocket handler in src/api/routes/websocket.py
- [x] T052 [US4] Update conversation.updated_at on new message in src/services/chat.py
- [x] T053 [US4] Create GET /conversations/search endpoint in src/api/routes/conversations.py
- [x] T054 [US4] Implement full-text search for messages in src/services/conversation.py

**Checkpoint**: Users can create, list, search conversations with unread counts

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T055 [P] Implement typing_start/typing_stop WebSocket handlers in src/api/routes/websocket.py
- [x] T056 [P] Implement typing_indicator broadcast in src/api/routes/websocket.py
- [x] T057 [P] Add structured logging throughout services in src/services/
- [x] T058 [P] Create POST /conversations/{id}/messages REST fallback endpoint in src/api/routes/messages.py
- [ ] T059 Validate all endpoints against OpenAPI contract in contracts/openapi.yaml
- [ ] T060 Run quickstart.md validation (full setup and test flow)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phases 3-6)**: All depend on Foundational completion
  - Can proceed in parallel if staffed
  - Or sequentially: US1 → US2 → US3 → US4
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational - No dependencies on other stories
- **US2 (P2)**: After Foundational - Uses Message model from US1 but independently testable
- **US3 (P3)**: After Foundational - Uses Presence model, independently testable
- **US4 (P4)**: After Foundational - Uses Conversation/Participant models, independently testable

### Within Each User Story

- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**:
- T003, T004, T005, T006 can run in parallel

**Phase 2 (Foundational)**:
- T011, T012, T013, T014 (models) can run in parallel
- T017, T018 (middleware) can run in parallel

**Phase 3 (US1)**:
- T020, T021 (models) can run in parallel

**Phase 6 (US4)**:
- T045, T046 (services) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch models in parallel:
Task: "Create Presence Pydantic model in src/models/presence.py"
Task: "Create WebSocket message schemas in src/models/websocket.py"

# Then services sequentially (depend on models):
Task: "Implement ChatService with send_message logic in src/services/chat.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test real-time messaging independently
5. Deploy/demo if ready - users can chat!

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test → Deploy (MVP: Real-time chat works!)
3. Add US2 → Test → Deploy (Now with message history)
4. Add US3 → Test → Deploy (Now with presence indicators)
5. Add US4 → Test → Deploy (Full conversation management)

### Parallel Team Strategy

With multiple developers after Foundational:
- Developer A: User Story 1 (messaging)
- Developer B: User Story 3 (presence) - can start immediately
- Developer C: User Story 4 (conversations) - can start immediately
- US2 (history) depends on US1 message storage, do after US1

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each user story independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
