"""
Database engine and session management.

Phase 1 uses SQLite (zero-setup, file-based) via the async aiosqlite driver.
Because we use SQLAlchemy's async ORM consistently, migrating to Postgres
later (Phase 3+) only requires changing DATABASE_URL and installing
asyncpg — no model or query code changes needed.
"""
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

Path("data").mkdir(exist_ok=True)

engine = create_async_engine(settings.database_url, echo=False, future=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Create all tables on startup. Idempotent — safe to call every boot."""
    async with engine.begin() as conn:
        from app.models import db_models  # noqa: F401 - ensures models are registered

        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a DB session per request."""
    async with async_session_factory() as session:
        yield session
