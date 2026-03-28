"""
Signal Hunter — FastAPI Application

The entry point for the backend. Creates the FastAPI app with:
- CORS middleware (for frontend communication)
- Lifespan management (startup/shutdown for services)
- Route registration
- Structured logging

In production, this runs behind Uvicorn on Railway.
In development, run with: `uvicorn app.main:app --reload --port 8000`
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.config import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan: startup and shutdown.

    Startup:
    - Validate all settings
    - Verify external service connectivity
    - Initialize APScheduler (Phase 1+)

    Shutdown:
    - Gracefully stop scheduler
    - Close HTTP clients
    """
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info(
        "Starting Signal Hunter v%s [%s]",
        settings.app_version,
        settings.environment.value,
    )

    # Log capability status
    logger.info("Claude API: configured")
    logger.info("Supabase: configured")
    logger.info("Upstash Redis: configured")
    logger.info(
        "Unusual Whales: %s",
        "configured" if settings.has_unusual_whales else "not configured (Phase 7)",
    )
    logger.info(
        "Twitter: %s",
        "configured" if settings.has_twitter else "not configured (Phase 3)",
    )
    logger.info(
        "Twilio SMS: %s",
        "configured" if settings.has_twilio else "not configured",
    )

    yield

    logger.info("Shutting down Signal Hunter")


def create_app() -> FastAPI:
    """
    Application factory.

    Creates and configures the FastAPI app. Using a factory pattern
    so tests can create fresh instances.
    """
    settings = get_settings()

    app = FastAPI(
        title="Signal Hunter",
        description="Decision intelligence terminal for markets",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # CORS — allow frontend to communicate
    # In production, this should be restricted to market-sentinel.com
    allowed_origins = ["http://localhost:3000"]
    if settings.is_production:
        allowed_origins = [
            "https://market-sentinel.com",
            "https://www.market-sentinel.com",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health_router, tags=["system"])

    return app


# The app instance — Uvicorn imports this
app = create_app()
