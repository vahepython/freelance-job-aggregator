from sqlalchemy import Integer
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declared_attr,
    mapped_column,
)
from app.core.config import settings

async_engine = create_async_engine(settings.database_url)
SessionFactory = async_sessionmaker(bind=async_engine, expire_on_commit=False)

class Model(DeclarativeBase):

    @declared_attr.directive
    def __tablename__(cls):
        return cls.__name__.lower()

    id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True, nullable=False, index=True)

async def db_session():
    async with async_session() as session:
        yield session
