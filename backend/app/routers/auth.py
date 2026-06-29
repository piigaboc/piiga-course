"""Authentication + TOTP MFA endpoints.

Mounted under ``/api/auth`` (the parent router carries the ``/api`` prefix,
this router adds ``/auth``).

Flow
----
1. ``POST /login`` -- verify email+password.
   * MFA on  -> ``{mfa_required: true, mfa_token: <pending JWT>}``.
   * MFA off -> ``{mfa_required: false, access_token: <access JWT>}``.
2. ``POST /mfa/verify`` -- exchange the pending token + a TOTP or backup code
   for a real access token.
3. ``POST /mfa/enroll`` -- (auth'd) generate a secret, store it un-enabled,
   return secret + otpauth uri.
4. ``POST /mfa/enroll/verify`` -- (auth'd) confirm a code, enable MFA, return
   one-time plaintext backup codes.
5. ``POST /mfa/disable`` -- (auth'd) require a valid TOTP code, clear MFA state.
6. ``GET /me`` -- (auth'd) current user.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User
from app.ratelimit import login_limiter, mfa_key, mfa_limiter
from app.schemas import (
    LoginRequest,
    LoginResponse,
    MfaDisableRequest,
    MfaEnrollResponse,
    MfaEnrollVerifyRequest,
    MfaEnrollVerifyResponse,
    MfaVerifyRequest,
    TokenResponse,
    UserOut,
)
from app.security import (
    create_access_token,
    create_mfa_pending_token,
    decode_mfa_pending_token,
    dummy_verify_password,
    generate_backup_codes,
    generate_totp_secret,
    get_current_user,
    totp_provisioning_uri,
    verify_and_consume_backup_code,
    verify_password,
    verify_totp,
    verify_totp_with_timestep,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Try to render a server-side SVG QR only if a library is already importable.
# We do NOT add a dependency for this; the frontend can draw from otpauth_uri.
try:  # pragma: no cover - environment dependent
    import segno  # type: ignore

    def _render_qr_svg(otpauth_uri: str) -> str | None:
        import io

        buf = io.BytesIO()
        segno.make(otpauth_uri).save(buf, kind="svg", xmldecl=False)
        return buf.getvalue().decode("utf-8")

except Exception:  # pragma: no cover - segno not installed

    def _render_qr_svg(otpauth_uri: str) -> str | None:
        return None


_invalid_credentials = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid credentials",
    headers={"WWW-Authenticate": "Bearer"},
)
_invalid_mfa = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired MFA challenge",
    headers={"WWW-Authenticate": "Bearer"},
)
_invalid_code = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid verification code",
)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Step one: verify email + password.

    Returns 401 ``Invalid credentials`` on any mismatch (we never reveal
    whether the email exists). After repeated failures the email is locked out
    for a cooldown period (429).
    """
    key = payload.email.strip().lower()
    login_limiter.check(key)

    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None:
        # Run a dummy verify so the unknown-email path takes the same time as
        # the wrong-password path (defeats a user-enumeration timing oracle).
        dummy_verify_password()
        login_limiter.record_failure(key)
        raise _invalid_credentials

    if not verify_password(payload.password, user.password_hash):
        login_limiter.record_failure(key)
        raise _invalid_credentials

    login_limiter.reset(key)

    if user.totp_enabled:
        return LoginResponse(
            mfa_required=True,
            mfa_token=create_mfa_pending_token(user.id),
        )

    return LoginResponse(
        mfa_required=False,
        access_token=create_access_token(user.id),
    )


@router.post("/mfa/verify", response_model=TokenResponse)
async def mfa_verify(
    payload: MfaVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Step two: exchange the pending token + a TOTP/backup code for access."""
    key = mfa_key()
    mfa_limiter.check(key)

    try:
        claims = decode_mfa_pending_token(payload.mfa_token)
        user_id = uuid.UUID(str(claims.get("sub")))
    except (JWTError, ValueError) as exc:
        mfa_limiter.record_failure(key)
        raise _invalid_mfa from exc

    user = await db.get(User, user_id)
    if user is None or not user.totp_enabled or not user.totp_secret:
        mfa_limiter.record_failure(key)
        raise _invalid_mfa

    timestep = verify_totp_with_timestep(user.totp_secret, payload.code)
    if timestep is not None:
        # Replay protection: reject a code whose timestep was already consumed
        # (within its still-valid window).
        if (
            user.last_totp_timestep is not None
            and timestep <= user.last_totp_timestep
        ):
            mfa_limiter.record_failure(key)
            raise _invalid_code
        user.last_totp_timestep = timestep
        await db.commit()
        mfa_limiter.reset(key)
        return TokenResponse(access_token=create_access_token(user.id))

    if await verify_and_consume_backup_code(user, payload.code, db):
        await db.commit()
        mfa_limiter.reset(key)
        return TokenResponse(access_token=create_access_token(user.id))

    mfa_limiter.record_failure(key)
    raise _invalid_code


@router.post("/mfa/enroll", response_model=MfaEnrollResponse)
async def mfa_enroll(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MfaEnrollResponse:
    """Begin enrollment: store a fresh (un-enabled) secret, return provisioning.

    Re-enrolling overwrites any previous not-yet-confirmed secret. MFA is not
    enabled until ``/mfa/enroll/verify`` succeeds. If MFA is already enabled,
    enrollment is rejected (disable first) so an active secret is never
    silently overwritten.
    """
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled. Disable it before re-enrolling.",
        )

    secret = generate_totp_secret()
    current_user.totp_secret = secret
    # Enrollment in progress; do not flip totp_enabled here.
    await db.commit()

    uri = totp_provisioning_uri(secret, current_user.email)
    return MfaEnrollResponse(
        secret=secret,
        otpauth_uri=uri,
        qr_svg=_render_qr_svg(uri),
    )


@router.post("/mfa/enroll/verify", response_model=MfaEnrollVerifyResponse)
async def mfa_enroll_verify(
    payload: MfaEnrollVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MfaEnrollVerifyResponse:
    """Confirm enrollment, enable MFA, and return one-time backup codes."""
    if not current_user.totp_secret:
        # Nothing pending to confirm.
        raise _invalid_code
    if not verify_totp(current_user.totp_secret, payload.code):
        raise _invalid_code

    plaintext, hashed = generate_backup_codes()
    current_user.totp_enabled = True
    current_user.backup_codes = hashed
    await db.commit()

    return MfaEnrollVerifyResponse(totp_enabled=True, backup_codes=plaintext)


@router.post("/mfa/disable", response_model=UserOut)
async def mfa_disable(
    payload: MfaDisableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Disable MFA. Requires a currently-valid TOTP code."""
    if not current_user.totp_enabled or not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )
    if not verify_totp(current_user.totp_secret, payload.code):
        raise _invalid_code

    current_user.totp_secret = None
    current_user.totp_enabled = False
    current_user.backup_codes = None
    await db.commit()

    return current_user


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user (no secrets)."""
    return current_user
