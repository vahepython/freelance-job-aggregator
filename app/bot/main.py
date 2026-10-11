import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.middleware.database import DatabaseMiddleware
from app.services.users import router as start_router
from app.core.config import settings
from app.core.redis_connect import redis_client
from app.bot.handlers.gmail import gmail_router


async def main():
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(gmail_router)
    dp.callback_query.middleware(DatabaseMiddleware)
    dp.message.middleware(DatabaseMiddleware)
    dp["redis_client"] = redis_client

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())