from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport

from fastapi import Request

from app.db.models.user import User

from redis.asyncio import Redis


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    user_query = select(User).where(User.telegram_id == user_id)
    user = await session.scalar(user_query)
    if not user:
        return None

    return user

def get_redis(request: Request) -> Redis:
    return request.app.state.redis_client

def get_async_client() -> AsyncClient:
    client = AsyncClient(transport=ASGITransport)
    return client