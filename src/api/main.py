"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.db.connection import init_db_pool, close_db_pool
from src.redis.connection import init_redis, close_redis
from src.redis.pubsub import pubsub_manager
from src.api.middleware.errors import setup_exception_handlers
from src.api.routes import websocket, messages, presence, conversations


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_db_pool()
    await init_redis()
    await pubsub_manager.start()
    yield
    # Shutdown
    await pubsub_manager.stop()
    await close_db_pool()
    await close_redis()


app = FastAPI(
    title="Real-time Chat API",
    version="1.0.0",
    description="REST API for chat conversations and message history",
    lifespan=lifespan,
)

# Setup exception handlers
setup_exception_handlers(app)

# Include routers
app.include_router(websocket.router, prefix="/api/v1", tags=["WebSocket"])
app.include_router(messages.router, prefix="/api/v1", tags=["Messages"])
app.include_router(presence.router, prefix="/api/v1", tags=["Presence"])
app.include_router(conversations.router, prefix="/api/v1", tags=["Conversations"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
