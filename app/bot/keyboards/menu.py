from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


COUNTRIES = {
    "am": "🇦🇲 Армения / Armenia",
    "az": "🇦🇿 Азербайджан / Azerbaijan",
    "by": "🇧🇾 Беларусь / Belarus",
    "ge": "🇬🇪 Грузия / Georgia",
    "kz": "🇰🇿 Казахстан / Kazakhstan",
    "kg": "🇰🇬 Кыргызстан / Kyrgyzstan",
    "md": "🇲🇩 Молдова / Moldova",
    "ru": "🇷🇺 Россия / Russia",
    "tj": "🇹🇯 Таджикистан / Tajikistan",
    "tm": "🇹🇲 Туркменистан / Turkmenistan",
    "uz": "🇺🇿 Узбекистан / Uzbekistan",
    "ua": "🇺🇦 Украина / Ukraine",
}


def country_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for code, label in COUNTRIES.items():
        builder.button(
            text=label,
            callback_data=f"country:{code}",
        )

    builder.adjust(2)

    builder.row(
        InlineKeyboardButton(
            text="🌍 Другая / Other",
            callback_data="country:other",
        )
    )

    return builder.as_markup()

def get_gmail_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Connect Gmail", callback_data="gmail_connect")
    return builder.as_markup()

def done_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Готово ✅ \n"
                        "Done ✅", callback_data="keyword_done")

    return builder.as_markup()