"""FastAPI dependency injection for DB and Redis."""

from typing import Annotated, AsyncGenerator

import asyncpg
import redis.asyncio as redis
from fastapi import Depends

from src.db.connection import get_connection, get_pool
from src.redis.connection import get_redis


async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Dependency for database connection."""
    async with get_connection() as conn:
        yield conn


async def get_db_pool_dep() -> asyncpg.Pool:
    """Dependency for database pool."""
    return get_pool()


async def get_redis_dep() -> redis.Redis:
    """Dependency for Redis client."""
    return get_redis()


# Type aliases for cleaner dependency injection
DBConnection = Annotated[asyncpg.Connection, Depends(get_db_connection)]
DBPool = Annotated[asyncpg.Pool, Depends(get_db_pool_dep)]
RedisClient = Annotated[redis.Redis, Depends(get_redis_dep)]
