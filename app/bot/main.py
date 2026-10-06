import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.middleware.database import DatabaseMiddleware
from app.services.users import router as start_router
from app.core.config import settings


async def main():
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.callback_query.middleware(DatabaseMiddleware)
    dp.message.middleware(DatabaseMiddleware)

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())