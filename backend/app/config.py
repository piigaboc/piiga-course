"""Application configuration via pydantic-settings.

Reads from environment variables and an optional ``.env`` file. This app is a
personal, SINGLE-USER course tracker running against a local PostgreSQL
instance, so connection handling uses a standard async pool (see ``db.py``).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
