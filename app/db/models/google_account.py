from datetime import datetime, UTC

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Model
from app.db.models.user import User


class GoogleAccount(Model):

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False,
                                         unique=True,
                                         ondelete="CASCADE")
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                               nullable=False,
                                               default=lambda: datetime.now(UTC))
    granted_scopes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    user: Mapped["User"] = relationship(
        back_populates="google_account",
    )