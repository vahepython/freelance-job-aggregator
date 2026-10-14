import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.handlers.gmail import gmail_router
from app.bot.middleware.database import DatabaseMiddleware
from app.core.config import settings
from app.core.redis_connect import redis_connection
from app.services.users import router as start_router


async def main():
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(gmail_router)

    dp.callback_query.middleware(DatabaseMiddleware())
    dp.message.middleware(DatabaseMiddleware())

    async with redis_connection() as redis_client:
        await dp.start_polling(
            bot,
            redis_client=redis_client,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())