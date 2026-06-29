"""Alembic environment, async (asyncpg) driver.

The URL comes from ``app.config.get_settings().DATABASE_URL`` (asyncpg DSN), so
there is one source of truth. Online migrations run inside a sync callback via
``connection.run_sync`` so the rest of Alembic stays synchronous.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Import settings + metadata. ``app.models`` registers every table on Base.
from app.config import get_settings
from app.db import Base
import app.models  # noqa: F401  (side-effect: populate Base.metadata)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the normalized async DSN from app settings. The raw ``DATABASE_URL``
# (which may be a raw Neon URL with ``sslmode=``/``channel_binding=``) is
# normalized to an asyncpg-safe URL; SSL is supplied via ``connect_args`` on the
# async engine below. See app.config.normalize_async_dsn.
config.set_main_option("sqlalchemy.url", get_settings().async_database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a DB connection (``--sql`` mode)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Create an async engine and run migrations through ``run_sync``."""
    settings = get_settings()
    connectable = create_async_engine(
        settings.async_database_url,
        poolclass=pool.NullPool,
        connect_args=settings.db_connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
