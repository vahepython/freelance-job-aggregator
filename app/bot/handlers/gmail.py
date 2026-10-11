import logging
import secrets

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from redis.asyncio import Redis
from redis.exceptions import (
    ConnectionError,
    DataError,
    ResponseError,
    TimeoutError,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.user import User


logger = logging.getLogger(__name__)
gmail_router = Router()


@gmail_router.callback_query(F.data == "gmail_connect")
async def gmail_connect(
    callback: CallbackQuery,
    session: AsyncSession,
    redis_client: Redis,
):
    await callback.answer()

    if not isinstance(callback.message, Message):
        return

    user = await session.scalar(
        select(User).where(
            User.telegram_id == callback.from_user.id
        )
    )

    if user is None:
        await callback.message.answer(
            "Сначала запусти /start.\n"
            "Please run /start first."
        )
        return

    ticket = secrets.token_urlsafe(32)

    try:
        await redis_client.set(
            name=f"gmail_connect:{ticket}",
            value=str(user.id),
            ex=600,
        )
    except (ConnectionError, TimeoutError, ResponseError, DataError):
        logger.exception(
            "Failed to save Gmail connection ticket in Redis"
        )
        await callback.message.answer(
            "Не удалось начать подключение. Попробуй позже.\n"
            "Could not start the connection. Please try again later."
        )
        return

    url = (
        f"{settings.api_base_url.rstrip('/')}/oauth/google/start"
        f"?ticket={ticket}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Продолжить подключение / Continue",
                    url=url,
                )
            ]
        ]
    )

    await callback.message.answer(
        "Нажми кнопку, чтобы подключить Gmail.\n"
        "Ссылка действует 10 минут.\n\n"
        "Press the button to connect Gmail.\n"
        "The link expires in 10 minutes.",
        reply_markup=keyboard,
    )
