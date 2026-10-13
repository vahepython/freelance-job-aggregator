from sqlalchemy import BigInteger, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Model

from app.bot.enums import CountryEnum
from app.db.models.google_account import GoogleAccount

class User(Model):

    telegram_id: Mapped[int] = mapped_column(BigInteger,unique=True, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    country: Mapped[CountryEnum | None] = mapped_column(
        Enum(
            CountryEnum,
            name="country_enum",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=True,
    )
    google_account: Mapped["GoogleAccount | None"] = relationship(
        back_populates="user",
        cascade="save-update, merge, delete, delete-orphan",
        passive_deletes=True,
    )
