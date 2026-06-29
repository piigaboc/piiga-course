"""Pytest fixtures for the auth + MFA API tests.

The production models target PostgreSQL (``UUID`` + ``ARRAY``). For fast,
dependency-light tests we run against an in-memory async SQLite database and
teach SQLite how to render those two Postgres types via ``@compiles`` hooks
(UUID -> CHAR(36), ARRAY -> JSON). This keeps the models untouched.
"""

from __future__ import annotations

import os

# SECRET_KEY is REQUIRED (no default) and must be >= 32 chars. Set a valid test
# value BEFORE any ``app.*`` import, because ``app.db`` calls ``get_settings()``
# at import time. Likewise leave BOOTSTRAP_* unset so startup seeding is a no-op.
os.environ.setdefault(
    "SECRET_KEY", "test-secret-key-0123456789abcdef-0123456789abcdef"
)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import asyncio  # noqa: E402
import json  # noqa: E402
from collections.abc import AsyncGenerator  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.dialects.postgresql import ARRAY, UUID  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles  # noqa: E402


# --- Make Postgres column types renderable on SQLite ----------------------
@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):  # noqa: ANN001, ANN201
    return "CHAR(36)"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(element, compiler, **kw):  # noqa: ANN001, ANN201
    return "JSON"


# Rendering ARRAY columns as JSON in DDL is not enough: when a *value* (a
# Python ``list``) is bound on SQLite, aiosqlite rejects the list parameter
# (``sqlite3.ProgrammingError``). Teach the Postgres ``ARRAY`` type how to
# (de)serialize on the SQLite dialect WITHOUT touching production models by
# attaching dialect-specific bind/result processors. ``ARRAY`` defines no
# processors of its own, so this only affects the SQLite test path; the
# native psycopg ARRAY codec on PostgreSQL is left completely untouched.
def _array_sqlite_bind_processor(self, dialect):  # noqa: ANN001, ANN202
    if dialect.name != "sqlite":
        return None

    def process(value):  # noqa: ANN001, ANN202
        if value is None:
            return None
        return json.dumps(list(value))

    return process


def _array_sqlite_result_processor(self, dialect, coltype):  # noqa: ANN001, ANN202
    if dialect.name != "sqlite":
        return None

    def process(value):  # noqa: ANN001, ANN202
        if value is None:
            return None
        if isinstance(value, (bytes, bytearray)):
            value = value.decode()
        return json.loads(value)

    return process


ARRAY.bind_processor = _array_sqlite_bind_processor
ARRAY.result_processor = _array_sqlite_result_processor


# Import models/app AFTER the compile hooks are registered.
from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():  # noqa: ANN201
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def _reset_rate_limiters():  # noqa: ANN201
    """Clear the in-process auth limiters so tests don't leak lockout state."""
    from app.ratelimit import login_limiter, mfa_limiter

    login_limiter._entries.clear()
    mfa_limiter._entries.clear()
    yield
    login_limiter._entries.clear()
    mfa_limiter._entries.clear()


@pytest_asyncio.fixture
async def engine():  # noqa: ANN201
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):  # noqa: ANN001, ANN201
    return async_sessionmaker(bind=engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(session_factory):  # noqa: ANN001, ANN201
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:  # noqa: ANN001
    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user(session_factory) -> User:  # noqa: ANN001
    """A persisted single user with a known password, MFA disabled."""
    async with session_factory() as session:
        u = User(
            email="me@example.com",
            password_hash=hash_password("s3cret-pw"),
            display_name="Me",
        )
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return u
