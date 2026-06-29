"""Tests for SECRET_KEY validation (B1) and bootstrap skip logic (H2)."""

from __future__ import annotations

import pytest

from app.config import Settings

pytestmark = pytest.mark.asyncio

_GOOD_SECRET = "x" * 32


def _settings(**overrides) -> Settings:  # noqa: ANN003
    base = {"SECRET_KEY": _GOOD_SECRET, "_env_file": None}
    base.update(overrides)
    return Settings(**base)


# --- B1: SECRET_KEY validation --------------------------------------------


def test_secret_key_required_rejects_empty():
    with pytest.raises(Exception):
        _settings(SECRET_KEY="")


def test_secret_key_rejects_placeholder():
    with pytest.raises(Exception):
        _settings(SECRET_KEY="change-me-in-production")


def test_secret_key_rejects_too_short():
    with pytest.raises(Exception):
        _settings(SECRET_KEY="short")


def test_secret_key_accepts_strong_value():
    s = _settings(SECRET_KEY=_GOOD_SECRET)
    assert s.SECRET_KEY == _GOOD_SECRET


# --- H2: bootstrap skip / create ------------------------------------------


async def test_bootstrap_skips_when_unset(monkeypatch, session_factory):
    from app import bootstrap as bootstrap_mod
    from app.models import User

    monkeypatch.setattr(
        bootstrap_mod,
        "get_settings",
        lambda: _settings(BOOTSTRAP_EMAIL="", BOOTSTRAP_PASSWORD=""),
    )
    async with session_factory() as session:
        created = await bootstrap_mod.bootstrap_user(session)
        assert created is None
        assert await session.scalar(__import__("sqlalchemy").select(User)) is None


async def test_bootstrap_skips_on_placeholder_password(
    monkeypatch, session_factory
):
    from app import bootstrap as bootstrap_mod
    from app.models import User

    monkeypatch.setattr(
        bootstrap_mod,
        "get_settings",
        lambda: _settings(
            BOOTSTRAP_EMAIL="me@example.com", BOOTSTRAP_PASSWORD="change-me"
        ),
    )
    async with session_factory() as session:
        created = await bootstrap_mod.bootstrap_user(session)
        assert created is None
        assert await session.scalar(__import__("sqlalchemy").select(User)) is None


async def test_bootstrap_creates_with_real_credentials(
    monkeypatch, session_factory
):
    from app import bootstrap as bootstrap_mod

    monkeypatch.setattr(
        bootstrap_mod,
        "get_settings",
        lambda: _settings(
            BOOTSTRAP_EMAIL="real@example.com",
            BOOTSTRAP_PASSWORD="a-strong-unique-password",
        ),
    )
    async with session_factory() as session:
        created = await bootstrap_mod.bootstrap_user(session)
        assert created is not None
        assert created.email == "real@example.com"
        # Idempotent: second call is a no-op.
        again = await bootstrap_mod.bootstrap_user(session)
        assert again is None
