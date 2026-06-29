"""Password hashing and JWT helpers.

Password hashing uses passlib's bcrypt. Access tokens are short-lived HS256
JWTs signed with ``SECRET_KEY``. ``get_current_user`` is a FastAPI dependency
that validates the Bearer token and loads the :class:`~app.models.User`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pyotp
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models import User

# Distinct ``typ`` claim marking a short-lived MFA-pending token. Access-token
# decode rejects this value; MFA-pending decode requires it. This guarantees a
# pending token can never authenticate a protected route, and vice-versa.
MFA_PENDING_TYP = "mfa_pending"

# --- Password hashing -----------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash for ``password``."""
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return ``True`` if ``password`` matches ``password_hash``."""
    return pwd_context.verify(password, password_hash)


# Precomputed bcrypt hash of a random throwaway value. When a login is attempted
# for an unknown email we still run ``verify_password`` against THIS hash so the
# response time matches the user-exists path, defeating a user-enumeration
# timing oracle. Computed once at import.
DUMMY_PASSWORD_HASH: str = pwd_context.hash("piigacourse-dummy-timing-password")


def dummy_verify_password() -> None:
    """Run a bcrypt verify against the dummy hash to equalize timing."""
    pwd_context.verify("piigacourse-dummy-timing-password", DUMMY_PASSWORD_HASH)


# --- JWT ------------------------------------------------------------------

ALGORITHM = "HS256"

# tokenUrl is informational (used by Swagger's auth form). The login route is
# wired in the auth task.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)


def create_access_token(
    subject: str | uuid.UUID,
    *,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed HS256 access token.

    ``subject`` becomes the ``sub`` claim (typically the user id). Lifetime
    defaults to ``ACCESS_TOKEN_EXPIRE_MIN`` from settings.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MIN)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a normal access JWT, returning its claims.

    Rejects MFA-pending tokens (``typ == "mfa_pending"``) so they can never be
    used to authenticate a protected route.

    Raises :class:`jose.JWTError` on an invalid/expired token, or on a token
    that carries the MFA-pending type.
    """
    settings = get_settings()
    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    if claims.get("typ") == MFA_PENDING_TYP:
        raise JWTError("MFA-pending token is not a valid access token")
    return claims


# --- MFA-pending token ----------------------------------------------------


def create_mfa_pending_token(user_id: str | uuid.UUID) -> str:
    """Create a SHORT-lived JWT proving step-one (password) succeeded.

    Lifetime is ``MFA_PENDING_EXPIRE_MIN``. It carries ``typ == "mfa_pending"``
    so :func:`decode_token` (and therefore ``get_current_user``) refuses it.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.MFA_PENDING_EXPIRE_MIN)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "typ": MFA_PENDING_TYP,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_mfa_pending_token(token: str) -> dict[str, Any]:
    """Decode an MFA-pending token, requiring ``typ == "mfa_pending"``.

    Rejects ordinary access tokens (missing the pending type). Raises
    :class:`jose.JWTError` on an invalid/expired/wrong-type token.
    """
    settings = get_settings()
    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    if claims.get("typ") != MFA_PENDING_TYP:
        raise JWTError("Not an MFA-pending token")
    return claims


# --- TOTP -----------------------------------------------------------------


def generate_totp_secret() -> str:
    """Return a fresh base32 TOTP secret."""
    return pyotp.random_base32()


def totp_provisioning_uri(
    secret: str, email: str, issuer: str = "PiigaCourse"
) -> str:
    """Build an ``otpauth://`` provisioning URI for authenticator apps."""
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    """Verify a TOTP ``code`` against ``secret`` (constant-time, +/-1 step)."""
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)


def verify_totp_with_timestep(
    secret: str, code: str, *, valid_window: int = 1
) -> int | None:
    """Verify a TOTP ``code`` and return the matched timestep counter.

    Scans the steps in ``[now - valid_window, now + valid_window]`` and returns
    the integer timestep (Unix time // 30) of the first match, or ``None`` if
    the code is invalid. The returned counter lets callers enforce single-use
    (replay protection) by rejecting any code whose timestep was already seen.
    """
    if not secret or not code:
        return None
    totp = pyotp.TOTP(secret)
    candidate = code.strip()
    now = datetime.now(timezone.utc)
    for offset in range(-valid_window, valid_window + 1):
        at = now + timedelta(seconds=offset * totp.interval)
        if pyotp.utils.strings_equal(str(totp.at(at)), candidate):
            return int(at.timestamp()) // totp.interval
    return None


# --- Backup codes ---------------------------------------------------------


def generate_backup_codes(n: int = 8) -> tuple[list[str], list[str]]:
    """Generate ``n`` single-use recovery codes.

    Returns ``(plaintext_list, hashed_list)``. Plaintext is shown to the user
    exactly once; only the hashes are persisted on the user.
    """
    plaintext: list[str] = []
    hashed: list[str] = []
    for _ in range(n):
        # 10 hex chars, grouped for readability (e.g. ``a1b2c-3d4e5``).
        raw = uuid.uuid4().hex[:10]
        code = f"{raw[:5]}-{raw[5:]}"
        plaintext.append(code)
        hashed.append(pwd_context.hash(code))
    return plaintext, hashed


async def verify_and_consume_backup_code(
    user: User, code: str, session: AsyncSession
) -> bool:
    """Check ``code`` against the user's stored backup-code hashes.

    On a match the consumed hash is removed (single use) and the change is
    flushed on ``session``; returns ``True``. Returns ``False`` otherwise.
    """
    if not code or not user.backup_codes:
        return False
    candidate = code.strip()
    for stored_hash in user.backup_codes:
        if pwd_context.verify(candidate, stored_hash):
            # Rebind the list so SQLAlchemy detects the mutation on the
            # ARRAY column (in-place mutation would not be tracked).
            user.backup_codes = [
                h for h in user.backup_codes if h != stored_hash
            ]
            await session.flush()
            return True
    return False


_credentials_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a Bearer token, or raise 401."""
    if not token:
        raise _credentials_exc
    try:
        claims = decode_token(token)
        subject = claims.get("sub")
        if subject is None:
            raise _credentials_exc
        user_id = uuid.UUID(str(subject))
    except (JWTError, ValueError) as exc:
        raise _credentials_exc from exc

    user = await db.get(User, user_id)
    if user is None:
        raise _credentials_exc
    return user
