from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from redis.asyncio import Redis

from app.core.config import settings


@asynccontextmanager
async def redis_connection() -> AsyncIterator[Redis]:
    client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )

    try:
        await client.ping()
        yield client
    finally:
        await client.aclose()