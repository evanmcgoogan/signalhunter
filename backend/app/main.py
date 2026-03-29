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

from app.api.events import router as events_router
from app.api.feed import router as feed_router
from app.api.health import router as health_router
from app.api.signals_api import router as signals_router
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

    # Initialize APScheduler for sensor polling (only if DB is configured)
    scheduler = None
    sensor_scheduler = None
    if settings.database_url:
        try:
            from apscheduler import AsyncScheduler
            from apscheduler.triggers.interval import IntervalTrigger

            from app.db import get_session_factory
            from app.deps import get_cache, get_claude
            from app.sensors.scheduler import SensorScheduler, get_poll_interval_seconds

            session_factory = get_session_factory()
            sensor_scheduler = SensorScheduler(
                cache=get_cache(),
                session_factory=session_factory,
                claude=get_claude(),
            )

            interval = get_poll_interval_seconds()
            scheduler = AsyncScheduler()
            await scheduler.__aenter__()
            await scheduler.add_schedule(
                sensor_scheduler.run_cycle,
                IntervalTrigger(seconds=interval),
                id="sensor_poll",
            )
            await scheduler.start_in_background()
            logger.info("Scheduler started: polling every %ds", interval)
        except Exception:
            logger.exception("Failed to start scheduler — running without polling")
            scheduler = None
    else:
        logger.warning("DATABASE_URL not set — scheduler disabled")

    yield

    # Shutdown
    if scheduler is not None:
        await scheduler.__aexit__(None, None, None)
    if sensor_scheduler is not None:
        await sensor_scheduler.shutdown()
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
    app.include_router(events_router, tags=["data"])
    app.include_router(signals_router, tags=["data"])
    app.include_router(feed_router, tags=["intelligence"])

    return app


# The app instance — Uvicorn imports this
app = create_app()
