import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, delete
import httpx

from fastapi import Request

from redis.asyncio import Redis
from collections.abc import AsyncIterator

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext

from app.core.config import settings
from app.db.models.keywords import Keyword
from app.db.models.user import User
from app.bot.keyboards.menu import done_keyboard


logger = logging.getLogger(__name__)

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
                         "Keywords setup"
                         "Keyboard setup",
                    callback_data="keywords_set",
                )
            ]
        ]
    )

    async with Bot(token=settings.bot_token).context() as bot:
        await bot.send_message(
            chat_id=chat_id,
            text="Gmail подключён ✅\nТеперь настрой ключевые слова. "
                 "Gmail connected ✅\n Now type the keywords. ",
            reply_markup=keyboard,
        )

async def finish_keywords(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    telegram_id: int,
):

    min_keywords = 3
    max_keywords = 10

    data = await state.get_data()
    words = list(dict.fromkeys(data.get("keywords", [])))

    if not min_keywords <= len(words) <= max_keywords:
        await message.answer("Нужно добавить от 3 до 10 keywords. "
                             "At least 3 keywords should be added. ")
        return

    try:
        user_id = await session.scalar(
            select(User.id).where(
                User.telegram_id == telegram_id
            )
        )

        if user_id is None:
            await message.answer(
                "Пользователь не найден. Запусти /start.\n"
                "User not found. Press /start"
            )
            return

        await session.execute(
            delete(Keyword).where(
                Keyword.user_id == user_id,
                Keyword.is_negative.is_(False),
            )
        )

        session.add_all(
            [
                Keyword(
                    user_id=user_id,
                    keywords=word,
                    weight=1,
                    is_negative=False,
                )
                for word in words
            ]
        )

        await session.commit()

    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to save keywords")

        await message.answer(
            "Не удалось сохранить keywords. "
            "Нажми «Готово», чтобы повторить."
            "Could not save the keywords.\n"
            "Press <Done> to restart' " ,
            reply_markup=done_keyboard(),
        )
        return

    await state.clear()

    await message.answer(
        "Keywords сохранены ✅\n"
        "Keywords are saved ✅\n"
        + ", ".join(words)
    )