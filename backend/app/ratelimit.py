"""In-process failed-attempt lockout (rate limiting).

Dependency-free (no redis) — this is a single-user app running as one process,
so a module-level dict is sufficient. Tracks consecutive failures per key and,
after ``MAX_FAILURES`` failures, locks the key for ``LOCKOUT_SECONDS``.

Usage::

    limiter = AttemptLimiter()
    limiter.check(key)            # raises 429 if locked
    ...                           # attempt the operation
    limiter.record_failure(key)   # on failure
    limiter.reset(key)            # on success

Not safe across multiple processes/hosts; intentionally minimal for this app.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from fastapi import HTTPException, status

# Tunables (module-level so tests can monkeypatch if needed).
MAX_FAILURES = 5
LOCKOUT_SECONDS = 60
# Sliding window in which consecutive failures accumulate. Failures older than
# this are forgotten (a stale single failure won't count toward a lockout).
WINDOW_SECONDS = 60


@dataclass
class _Entry:
    failures: int = 0
    first_failure_at: float = 0.0
    locked_until: float = 0.0


class AttemptLimiter:
    """Thread-safe in-process consecutive-failure lockout."""

    def __init__(
        self,
        *,
        max_failures: int = MAX_FAILURES,
        lockout_seconds: int = LOCKOUT_SECONDS,
        window_seconds: int = WINDOW_SECONDS,
    ) -> None:
        self.max_failures = max_failures
        self.lockout_seconds = lockout_seconds
        self.window_seconds = window_seconds
        self._entries: dict[str, _Entry] = {}
        self._lock = threading.Lock()

    def _now(self) -> float:
        return time.monotonic()

    def check(self, key: str) -> None:
        """Raise 429 if ``key`` is currently locked out."""
        now = self._now()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return
            if entry.locked_until > now:
                retry_after = int(entry.locked_until - now) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        "Too many failed attempts. Try again in "
                        f"{retry_after} seconds."
                    ),
                    headers={"Retry-After": str(retry_after)},
                )
            # Lock expired: clear it so the counter starts fresh.
            if entry.locked_until and entry.locked_until <= now:
                self._entries.pop(key, None)

    def record_failure(self, key: str) -> None:
        """Record a failed attempt; lock the key once the threshold is hit."""
        now = self._now()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or (
                entry.first_failure_at
                and now - entry.first_failure_at > self.window_seconds
            ):
                entry = _Entry(failures=0, first_failure_at=now)
                self._entries[key] = entry

            entry.failures += 1
            if entry.failures >= self.max_failures:
                entry.locked_until = now + self.lockout_seconds

    def reset(self, key: str) -> None:
        """Clear all failure state for ``key`` (call on success)."""
        with self._lock:
            self._entries.pop(key, None)


# Shared limiters for the auth endpoints. Login is keyed per-email; MFA verify
# is global (single-user app, one secret).
login_limiter = AttemptLimiter()
mfa_limiter = AttemptLimiter()

_MFA_GLOBAL_KEY = "mfa-verify"


def mfa_key() -> str:
    return _MFA_GLOBAL_KEY
