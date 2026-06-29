"""Pydantic v2 request/response models for the auth + MFA API.

API contract (all routes mounted under ``/api/auth`` -- see
:mod:`app.routers.auth`). Passwords, password hashes, TOTP secrets, and backup
code hashes are NEVER serialised in a response model; ``secret`` /
``backup_codes`` are returned exactly once at enrollment time via the dedicated
enrollment responses below.
"""

from __future__ import annotations

import uuid
from datetime import date as date_type, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import CourseStatus


# --- Login / token --------------------------------------------------------


class LoginRequest(BaseModel):
    """Step-one credentials for password login."""

    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    """Result of ``POST /api/auth/login``.

    If MFA is enabled, ``mfa_required`` is ``True`` and ``mfa_token`` carries a
    short-lived pending JWT to exchange at ``/api/auth/mfa/verify``; in that
    case ``access_token`` is ``None``. Otherwise ``access_token`` is populated
    and ``mfa_token`` is ``None``.
    """

    mfa_required: bool
    mfa_token: str | None = None
    access_token: str | None = None
    token_type: str = "bearer"


class MfaVerifyRequest(BaseModel):
    """Step-two MFA challenge: exchange a pending token + TOTP/backup code."""

    mfa_token: str
    code: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """A bare access token (issued after a successful MFA verify)."""

    access_token: str
    token_type: str = "bearer"


# --- MFA enrollment -------------------------------------------------------


class MfaEnrollResponse(BaseModel):
    """Result of ``POST /api/auth/mfa/enroll``.

    Returns the freshly generated (not-yet-enabled) TOTP ``secret`` and an
    ``otpauth_uri`` for QR provisioning. ``qr_svg`` is a pre-rendered SVG when
    the server can produce one cheaply, else ``None`` and the client draws the
    QR from ``otpauth_uri``.
    """

    secret: str
    otpauth_uri: str
    qr_svg: str | None = None


class MfaEnrollVerifyRequest(BaseModel):
    """Confirm enrollment by proving possession of the authenticator."""

    code: str = Field(min_length=1)


class MfaEnrollVerifyResponse(BaseModel):
    """One-time delivery of plaintext backup codes after enabling MFA."""

    totp_enabled: bool = True
    backup_codes: list[str]


class MfaDisableRequest(BaseModel):
    """Disable MFA; requires a currently-valid TOTP code."""

    code: str = Field(min_length=1)


# --- User -----------------------------------------------------------------


class UserOut(BaseModel):
    """Public view of the user. No secrets/credentials are exposed."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str | None = None
    totp_enabled: bool


# --- Courses --------------------------------------------------------------


class CourseCreate(BaseModel):
    """Payload to create a tracked course."""

    title: str = Field(min_length=1, max_length=300)
    platform: str | None = Field(default=None, max_length=120)
    url: str | None = Field(default=None, max_length=2048)
    status: CourseStatus = CourseStatus.planned
    target_date: date_type | None = None


class CourseUpdate(BaseModel):
    """Partial update for a course (every field optional)."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    platform: str | None = Field(default=None, max_length=120)
    url: str | None = Field(default=None, max_length=2048)
    status: CourseStatus | None = None
    target_date: date_type | None = None


class CourseOut(BaseModel):
    """Public view of a course."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    platform: str | None = None
    url: str | None = None
    status: CourseStatus
    target_date: date_type | None = None
    created_at: datetime
    updated_at: datetime


# --- Study sessions -------------------------------------------------------


class SessionCreate(BaseModel):
    """Payload to log a study session against a course."""

    date: date_type
    minutes: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=1000)


class SessionOut(BaseModel):
    """Public view of a study session."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    date: date_type
    minutes: int
    note: str | None = None
    created_at: datetime


# --- Calendar -------------------------------------------------------------


class CalendarDay(BaseModel):
    """Aggregated study activity for a single calendar day."""

    date: date_type
    total_minutes: int
    session_count: int
    course_ids: list[uuid.UUID]


class CalendarResponse(BaseModel):
    """Study activity for a month, one entry per studied day."""

    month: str
    days: list[CalendarDay]


# --- Stats ----------------------------------------------------------------


class StatsOut(BaseModel):
    """Dashboard summary statistics for the single user."""

    active_courses: int
    completed_courses: int
    total_courses: int
    total_minutes: int
    total_hours: float
    current_streak: int
    sessions_this_week: int
