"""Async database layer (SQLAlchemy 2.0 style).

Single-user app on a *local* PostgreSQL instance, so we use a STANDARD async
connection pool (the default ``AsyncAdaptedQueuePool``) rather than ``NullPool``.
There is no PgBouncer / serverless concern here.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# Build engine kwargs conditionally. SQLite (tests / in-memory) uses a
# StaticPool that REJECTS queue-pool tuning kwargs (``pool_size`` /
# ``max_overflow`` / ``pool_pre_ping``), so we only pass those for real
# server-backed databases (e.g. PostgreSQL).
_engine_kwargs: dict = {"echo": False}
if not settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs.update(
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

# Standard async engine. For Postgres this keeps the default queue pool with
# the production tuning; for SQLite it falls back to the dialect default pool.
engine = create_async_engine(
    settings.DATABASE_URL,
    **_engine_kwargs,
)

# Session factory. ``expire_on_commit=False`` keeps ORM objects usable after
# commit inside request handlers.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models (defined in later tasks)."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped ``AsyncSession``.

    The session is closed when the request finishes.
    """
    async with AsyncSessionLocal() as session:
        yield session
