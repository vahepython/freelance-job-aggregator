from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.db.models.user import User

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import  Integer, Boolean, Text, ForeignKey, UniqueConstraint

from app.db.base import Model

class Keyword(Model):


    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "keywords",
            "is_negative",
            name="uq_keywords_user_text_negative",
        ),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
                                         index=True,
                                         )
    keywords: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_negative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="False")
    user: Mapped["User"] = relationship(back_populates="keywords")