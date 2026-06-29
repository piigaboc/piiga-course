"""Application configuration via pydantic-settings.

Reads from environment variables and an optional ``.env`` file. This app is a
personal, SINGLE-USER course tracker running against a local PostgreSQL
instance, so connection handling uses a standard async pool (see ``db.py``).
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# libpq-only query params that asyncpg.connect() does NOT accept. They are
# valid in a Neon/psql connection string but must be stripped before the URL
# reaches asyncpg (SSL is instead passed via connect_args ``ssl=``).
_LIBPQ_ONLY_PARAMS = frozenset(
    {
        "sslmode",
        "channel_binding",
        "gssencmode",
        "target_session_attrs",
        "sslrootcert",
        "sslcert",
        "sslkey",
        "sslnegotiation",
        "options",
    }
)

# sslmode values (or its presence) that mean "use SSL".
_SSL_REQUIRING_MODES = frozenset(
    {"require", "verify-ca", "verify-full", "prefer", "allow"}
)

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", ""})


def normalize_async_dsn(raw: str) -> tuple[str, dict]:
    """Normalize an arbitrary Postgres DSN into an asyncpg-safe form.

    Accepts any of:
      * ``postgresql://...?sslmode=require&channel_binding=require`` (Neon)
      * ``postgres://...``
      * ``postgresql+asyncpg://...`` (already correct)
      * ``postgresql+asyncpg://piiga:piiga@localhost:5432/piigacourse`` (local)
      * ``sqlite+aiosqlite://...`` (tests — passed through untouched)

    Returns ``(async_url, connect_args)`` where:
      * scheme is rewritten to ``postgresql+asyncpg`` (any other ``+driver`` is
        replaced; an existing ``+asyncpg`` is preserved),
      * libpq-only query params (``sslmode``, ``channel_binding``, ...) are
        removed from the URL, and
      * ``connect_args`` is ``{"ssl": <SSLContext>}`` when SSL is needed
        (sslmode requested SSL, or the host is non-local), else ``{}``.
    """
    parts = urlsplit(raw)
    scheme = parts.scheme.lower()

    # Non-postgres DSNs (e.g. sqlite for tests) pass through unchanged.
    if not (scheme == "postgres" or scheme.startswith("postgresql")):
        return raw, {}

    # --- Rewrite scheme -> postgresql+asyncpg ------------------------------
    if "+" in scheme:
        driver = scheme.split("+", 1)[1]
        if driver != "asyncpg":
            scheme = "postgresql+asyncpg"
    else:
        # "postgres" or "postgresql" with no driver.
        scheme = "postgresql+asyncpg"

    # --- Inspect + strip libpq-only query params ---------------------------
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    sslmode_value = None
    kept_pairs = []
    for key, value in pairs:
        lkey = key.lower()
        if lkey == "sslmode":
            sslmode_value = value.lower()
        if lkey in _LIBPQ_ONLY_PARAMS:
            continue
        kept_pairs.append((key, value))
    cleaned_query = urlencode(kept_pairs)

    # --- Decide whether SSL is required ------------------------------------
    host = (parts.hostname or "").lower()
    is_local = host in _LOCAL_HOSTS
    ssl_required = False
    if sslmode_value is not None:
        ssl_required = sslmode_value in _SSL_REQUIRING_MODES
    elif not is_local:
        # Remote host with no explicit sslmode (e.g. an already-asyncpg Neon
        # URL): default to requiring SSL.
        ssl_required = True

    async_url = urlunsplit(
        (scheme, parts.netloc, parts.path, cleaned_query, parts.fragment)
    )

    connect_args: dict = {}
    if ssl_required:
        import ssl as _ssl

        connect_args["ssl"] = _ssl.create_default_context()

    return async_url, connect_args


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Values are sourced from environment variables (case-insensitive) or a
    local ``.env`` file. Unknown env vars are ignored.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database -----------------------------------------------------------
    # SQLAlchemy async DSN. Local Postgres by default.
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://piiga:piiga@localhost:5432/piigacourse",
    )

    # --- Security / JWT -----------------------------------------------------
    # REQUIRED. No default: pydantic raises if it is unset. Must be a strong,
    # random value of at least 32 chars (e.g. ``openssl rand -hex 32``).
    SECRET_KEY: str = Field(...)
    ACCESS_TOKEN_EXPIRE_MIN: int = Field(default=60)
    # Window an MFA challenge stays valid before a fresh login is required.
    MFA_PENDING_EXPIRE_MIN: int = Field(default=5)

    # --- CORS ---------------------------------------------------------------
    # Stored as a plain comma-separated STRING. Keeping it a ``str`` avoids
    # pydantic-settings v2 trying to ``json.loads()`` the raw env value (which
    # it does for list/complex types, before any validator runs). The parsed
    # ``list[str]`` is exposed via the ``cors_origins_list`` computed property.
    CORS_ORIGINS: str = Field(default="http://localhost:5173")

    # --- Single-user bootstrap ---------------------------------------------
    # Credentials used to seed the one and only account on first run. Both must
    # be supplied (and the password must not be a placeholder) for the account
    # to be created; otherwise bootstrap SKIPS seeding (see app.bootstrap).
    BOOTSTRAP_EMAIL: str = Field(default="")
    BOOTSTRAP_PASSWORD: str = Field(default="")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_database_url(self) -> str:
        """``DATABASE_URL`` normalized to an asyncpg-safe URL.

        Scheme is forced to ``postgresql+asyncpg`` and libpq-only query params
        (``sslmode``, ``channel_binding``, ...) are stripped so the raw Neon URL
        can be pasted into ``DATABASE_URL`` directly. See ``normalize_async_dsn``.
        """
        return normalize_async_dsn(self.DATABASE_URL)[0]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def db_connect_args(self) -> dict:
        """``connect_args`` for the async engine derived from ``DATABASE_URL``.

        ``{"ssl": <SSLContext>}`` when SSL is required (Neon / any non-local
        host or explicit ``sslmode=require``), else ``{}`` (local dev / sqlite).
        """
        return normalize_async_dsn(self.DATABASE_URL)[1]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse ``CORS_ORIGINS`` into a list of origins.

        Splits the comma-separated string, strips whitespace, and drops empty
        entries. Use this anywhere a ``list[str]`` of origins is required.
        """
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @field_validator("SECRET_KEY")
    @classmethod
    def _validate_secret_key(cls, value: str) -> str:
        """Reject empty / placeholder / too-short secrets.

        SECRET_KEY signs every JWT, so a weak value lets anyone forge tokens.
        Require a non-placeholder value of at least 32 characters.
        """
        placeholders = {
            "change-me-in-production",
            "change-me",
            "replace-with-a-long-random-secret",
            "secret",
            "changeme",
        }
        stripped = (value or "").strip()
        if not stripped:
            raise ValueError(
                "SECRET_KEY is required and must not be empty. Generate one "
                "with: openssl rand -hex 32"
            )
        if stripped.lower() in placeholders:
            raise ValueError(
                "SECRET_KEY is set to a known placeholder. Generate a real "
                "random value with: openssl rand -hex 32"
            )
        if len(stripped) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters. Generate one with: "
                "openssl rand -hex 32"
            )
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance (one per process)."""
    return Settings()
