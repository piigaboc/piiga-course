"""Single-user bootstrap.

Creates the one and only :class:`~app.models.User` from ``BOOTSTRAP_EMAIL`` /
``BOOTSTRAP_PASSWORD`` if the table is empty. Idempotent: a no-op once any user
exists. Invoked on app startup (see :mod:`app.main`) and runnable directly via
``python -m app.bootstrap``.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.models import User
from app.security import hash_password

logger = logging.getLogger(__name__)

# Known placeholder passwords we refuse to seed a real account with.
_PLACEHOLDER_PASSWORDS = {
    "change-me",
    "change-me-in-production",
    "changeme",
    "password",
    "secret",
}


async def bootstrap_user(session: AsyncSession) -> User | None:
    """Seed the single user if none exists.

    Returns the newly created ``User`` on first run, or ``None`` if a user was
    already present (idempotent) OR if the bootstrap credentials are missing /
    placeholder. We never create a guessable account: if ``BOOTSTRAP_EMAIL`` or
    ``BOOTSTRAP_PASSWORD`` is unset/empty, or the password is a known
    placeholder, we log a loud warning and skip seeding.
    """
    settings = get_settings()

    existing = await session.scalar(select(User).limit(1))
    if existing is not None:
        return None

    email = (settings.BOOTSTRAP_EMAIL or "").strip()
    password = settings.BOOTSTRAP_PASSWORD or ""

    if not email or not password:
        logger.warning(
            "Bootstrap SKIPPED: BOOTSTRAP_EMAIL and/or BOOTSTRAP_PASSWORD are "
            "unset. No account was created. Set both to seed the single user."
        )
        return None

    if password.strip().lower() in _PLACEHOLDER_PASSWORDS:
        logger.warning(
            "Bootstrap SKIPPED: BOOTSTRAP_PASSWORD is a known placeholder. "
            "Refusing to create a guessable account. Set a strong password to "
            "seed the single user."
        )
        return None

    user = User(
        email=email,
        password_hash=hash_password(password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    logger.info("Bootstrap: created single user %s.", user.email)
    return user


async def _run() -> None:
    async with AsyncSessionLocal() as session:
        created = await bootstrap_user(session)
        if created is None:
            print("Bootstrap: user already exists, nothing to do.")
        else:
            print(f"Bootstrap: created user {created.email} ({created.id}).")


if __name__ == "__main__":
    asyncio.run(_run())
