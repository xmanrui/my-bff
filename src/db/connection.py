"""PostgreSQL connection pool management."""

import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration from environment."""

    database_url: str = "postgresql://postgres:postgres@localhost:5432/chat"

    class Config:
        env_file = ".env"


_pool: asyncpg.Pool | None = None


async def init_db_pool() -> asyncpg.Pool:
    """Initialize the database connection pool."""
    global _pool
    if _pool is None:
        settings = DatabaseSettings()
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=5,
            max_size=20,
            command_timeout=60,
        )
    return _pool


async def close_db_pool() -> None:
    """Close the database connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Get the current connection pool."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db_pool() first.")
    return _pool


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get a database connection from the pool."""
    pool = get_pool()
    async with pool.acquire() as connection:
        yield connection
