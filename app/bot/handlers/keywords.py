import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
)
from sqlalchemy import  select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import Keywords
from app.db.models.google_account import GoogleAccount
from app.db.models.user import User
from app.services.keywords import resolve_keyword
from app.bot.keyboards.menu import done_keyboard
from app.services.utilities import finish_keywords


logger = logging.getLogger(__name__)
keywords_router = Router()

MIN_KEYWORDS = 3
MAX_KEYWORDS = 10


@keywords_router.callback_query(F.data == "keywords_set")
async def start_keywords(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
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
            "Сначала запусти /start."
        )
        return

    google_account_id = await session.scalar(
        select(GoogleAccount.id).where(
            GoogleAccount.user_id == user.id
        )
    )

    if google_account_id is None:
        await callback.message.answer(
            "Сначала подключи Gmail."
        )
        return

    current_state = await state.get_state()

    if current_state == Keywords.waiting_for_keywords.state:
        await callback.message.answer(
            "Ввод уже начат. Отправь следующую технологию."
        )
        return

    await state.set_data({"keywords": []})
    await state.set_state(Keywords.waiting_for_keywords)

    await callback.message.answer(
        "Отправляй по одной технологии или фразе.\n"
        "Например: Python или Docker Compose.\n"
        "Можно добавить от 3 до 10 keywords.\n"
        "После трёх появится кнопка «Готово».\n"
        "Новый список заменит твои положительные keywords."
    )


@keywords_router.message(Keywords.waiting_for_keywords, F.text)
async def receive_keyword(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    if message.from_user is None:
        return

    data = await state.get_data()
    words = list(data.get("keywords", []))

    if len(words) >= MAX_KEYWORDS:
        await message.answer(
            "Достигнут лимит 10 keywords. Нажми «Готово».",
            reply_markup=done_keyboard(),
        )
        return

    keyword = resolve_keyword(message.text)

    if keyword is None:
        await message.answer(
            "Не удалось распознать keyword.\n"
            "Отправь одну технологию или фразу.\n"
            "Например: Python или Docker Compose."
        )
        return

    if keyword in words:
        await message.answer(
            "Этот keyword уже добавлен."
        )
        return

    words.append(keyword)
    await state.update_data(keywords=words)

    if len(words) == MAX_KEYWORDS:
        await finish_keywords(
            message=message,
            state=state,
            session=session,
            telegram_id=message.from_user.id,
        )
        return

    await message.answer(
        f"Добавлено: {keyword} ✅\n"
        f"Всего: {len(words)}/{MAX_KEYWORDS}\n\n"
        f"Твой список: {', '.join(words)}",
        reply_markup=(
            done_keyboard
            if len(words) >= MIN_KEYWORDS
            else None
        ),
    )


@keywords_router.message(Keywords.waiting_for_keywords)
async def receive_non_text(message: Message):
    await message.answer(
        "Отправь keyword текстовым сообщением."
    )


@keywords_router.callback_query(F.data == "keywords_done")
async def confirm_keywords(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
):
    await callback.answer()

    if not isinstance(callback.message, Message):
        return

    current_state = await state.get_state()

    if current_state != Keywords.waiting_for_keywords.state:
        await callback.message.answer(
            "Этот ввод уже завершён. "
            "Нажми «Настроить keywords» для нового списка."
        )
        return

    await finish_keywords(
        message=callback.message,
        state=state,
        session=session,
        telegram_id=callback.from_user.id,
    )