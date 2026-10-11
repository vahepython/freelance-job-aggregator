from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.user import User

from redis.asyncio import Redis
from app.core.redis_connect import redis_client as shared_redis_client


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    user_query = select(User).where(User.telegram_id == user_id)
    user = await session.scalar(user_query)
    if not user:
        return None

    return user

def get_redis() -> Redis:
    return shared_redis_client