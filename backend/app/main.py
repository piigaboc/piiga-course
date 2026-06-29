"""FastAPI application factory and entrypoint.

Exposes a module-level ``app`` (``app.main:app``) for uvicorn.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bootstrap import bootstrap_user
from app.config import get_settings
from app.db import AsyncSessionLocal
from app.routers import auth as auth_router
from app.routers import courses as courses_router
from app.routers import sessions as sessions_router
from app.routers import stats as stats_router

# All routes live under /api.
api_router = APIRouter(prefix="/api")


@api_router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness check (public)."""
    return {"status": "ok"}


# Auth + MFA routes -> /api/auth/...
api_router.include_router(auth_router.router)
# Course tracker -> /api/courses, /api/sessions, /api/stats
api_router.include_router(courses_router.router)
api_router.include_router(sessions_router.router)
api_router.include_router(stats_router.router)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Seed the single user on startup (no-op if one already exists)."""
    async with AsyncSessionLocal() as session:
        await bootstrap_user(session)
    yield


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="PiigaCourse API",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        # Bearer tokens are sent from localStorage in the Authorization header,
        # not via cookies, so credentialed CORS is unnecessary (and would
        # forbid the "*" origin pattern). Keep it off.
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
