"""Redis connection management."""

import redis.asyncio as redis
from pydantic_settings import BaseSettings


class RedisSettings(BaseSettings):
    """Redis configuration from environment."""

    redis_url: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"


_redis_client: redis.Redis | None = None


async def init_redis() -> redis.Redis:
    """Initialize the Redis client."""
    global _redis_client
    if _redis_client is None:
        settings = RedisSettings()
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


def get_redis() -> redis.Redis:
    """Get the current Redis client."""
    if _redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_client
