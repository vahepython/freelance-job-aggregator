from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fastapi import Request

from app.db.models.user import User

from redis.asyncio import Redis

from collections.abc import AsyncIterator

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.config import settings

import httpx


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    user_query = select(User).where(User.telegram_id == user_id)
    user = await session.scalar(user_query)
    if not user:
        return None

    return user

def get_redis(request: Request) -> Redis:
    return request.app.state.redis_client


async def get_async_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        yield client




async def notify_gmail_connected(chat_id: int):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Настроить keywords\n"
                         "Keyboard setup",
                    callback_data="keywords_set",
                )
            ]
        ]
    )

    async with Bot(token=settings.bot_token).context() as bot:
        await bot.send_message(
            chat_id=chat_id,
            text="Gmail подключён ✅\nТеперь настрой ключевые слова.",
            reply_markup=keyboard,
        )