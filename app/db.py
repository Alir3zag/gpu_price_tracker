# app/db.py
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Boolean, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship

from app.config import DB_PATH

DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email      = Column(String, nullable=False, unique=True)
    password   = Column(String, nullable=False)             # hashed — never plain text
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    settings   = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    alerts     = relationship("PriceAlert", back_populates="user", cascade="all, delete-orphan")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id                     = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id                = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    email_enabled          = Column(Boolean, default=False)
    alert_threshold        = Column(Float, default=5.0)         # % drop to trigger alert
    check_interval_hours   = Column(Float, default=6.0)
    search_queries         = Column(String, default="3090,3080,4090")   # comma-separated
    user                   = relationship("User", back_populates="settings")


class GPUPrice(Base):
    __tablename__ = "gpu_prices"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name       = Column(String, nullable=False)                 # full product name
    price      = Column(Float, nullable=False)
    link       = Column(String)
    query      = Column(String)                                 # which search produced this
    retailer   = Column(String, default="newegg")               # ready for multi-retailer Stage 4
    scraped_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String, ForeignKey("users.id"), nullable=False)
    gpu_name   = Column(String, nullable=False)
    old_price  = Column(Float, nullable=False)
    new_price  = Column(Float, nullable=False)
    drop_pct   = Column(Float, nullable=False)
    link       = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user       = relationship("User", back_populates="alerts")


engine        = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session