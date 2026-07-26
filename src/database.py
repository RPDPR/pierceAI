import os
from datetime import datetime
from typing import List
from sqlalchemy import BigInteger, ForeignKey, String, Text, DateTime, UniqueConstraint, Boolean, Float, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://bot_user:bot_password_123@db:5432/pierceai_db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    author_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

class ChannelConfig(Base):
    __tablename__ = "channels_config"

    channel_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    allow_read: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_write: Mapped[bool] = mapped_column(Boolean, default=True)
    cooldown: Mapped[float] = mapped_column(Float, default=0.0)

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)