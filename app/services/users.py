import logging

from aiogram import  Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.bot.keyboards.menu import country_keyboard
from app.db.models.user import User
from app.bot.enums import CountryEnum
from app.services.utilities import get_user

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart(), F.chat.type == "private")
async def welcome_user(message: Message, session: AsyncSession):
    user = await get_user(session, message.from_user.id)
    if user is None:
        new_user = User(telegram_id=message.from_user.id,
                        chat_id=message.chat.id,
                        country=None)
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        welcome_text = (
            "Привет! 👋 Добро пожаловать в Freelance Job Aggregator.\n\n"
            "Я отбираю подходящие freelance-заказы из email-уведомлений "
            "и отправляю их в Telegram.\n"
            "Подключи Gmail, на который приходят уведомления площадок, "
            "и укажи интересующие технологии.\n\n"
            "🌍 Для начала выбери свою страну. "
            "Если её нет в списке, нажми «Другая / Other».\n\n"
            "Welcome to Freelance Job Aggregator! 👋\n\n"
            "I filter freelance job alerts from your email "
            "and send matching opportunities to Telegram.\n"
            "Connect the Gmail account that receives alerts from freelance platforms "
            "and add the technologies you’re interested in.\n\n"
            "🌍 First, select your country. "
            "If it isn’t listed, tap “Другая / Other”."
        )
        await message.answer(text=welcome_text
                             )
    elif user.country is None:
        await message.answer(
            "Выбери страну / Select your country:",
            reply_markup=country_keyboard(),
        )
    else:
        await message.answer("С возвращением! / Welcome back!")



@router.callback_query(F.data.startswith("country:"))
async def select_country(
    callback: CallbackQuery,
    session: AsyncSession,
):
    if (
        not isinstance(callback.message, Message)
        or callback.message.chat.type != "private"
    ):
        await callback.answer(
            "Открой личный чат с ботом / Open a private chat with the bot",
            show_alert=True,
        )
        return

    country_code = callback.data.split(":", 1)[1]

    try:
        country = CountryEnum(country_code)
    except ValueError:
        await callback.answer(
            "Неизвестная страна / Invalid country",
            show_alert=True,
        )
        return

    user = await get_user(session, callback.from_user.id)

    if user is None:
        await callback.answer(
            "Сначала отправь /start / Send /start first",
            show_alert=True,
        )
        return

    if user.country is not None:
        await callback.answer(
            "Страна уже выбрана / Country already selected",
        )
        return

    user.country = country

    try:
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to save user country")
        await callback.answer(
            "Не удалось сохранить. Попробуй снова / Could not save. Try again",
            show_alert=True,
        )
        return

    await callback.answer(
        "Страна сохранена / Country saved",
    )

    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        "Страна сохранена ✅\n"
        "Следующий шаг — подключить Gmail.\n\n"
        "Country saved ✅\n"
        "Next, connect your Gmail account."
    )