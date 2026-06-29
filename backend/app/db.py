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

# The connection URL is normalized to an asyncpg-safe form (scheme rewritten,
# libpq-only query params stripped) and SSL is supplied via ``connect_args``
# (asyncpg wants ``ssl=``, not ``sslmode=``). This lets a raw Neon Postgres URL
# be pasted into ``DATABASE_URL`` unchanged. See app.config.normalize_async_dsn.
_database_url = settings.async_database_url

# Build engine kwargs conditionally. SQLite (tests / in-memory) uses a
# StaticPool that REJECTS queue-pool tuning kwargs (``pool_size`` /
# ``max_overflow`` / ``pool_pre_ping``), so we only pass those for real
# server-backed databases (e.g. PostgreSQL). SQLite also never needs SSL
# connect_args (``db_connect_args`` is ``{}`` for it).
_engine_kwargs: dict = {"echo": False}
if not _database_url.startswith("sqlite"):
    _engine_kwargs.update(
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args=settings.db_connect_args,
    )

# Standard async engine. For Postgres this keeps the default queue pool with
# the production tuning; for SQLite it falls back to the dialect default pool.
engine = create_async_engine(
    _database_url,
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
