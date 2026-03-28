"""
Signal Hunter — Health Check Endpoint

Deep health check that verifies all external dependencies.
Used by Railway for health monitoring and by the frontend
to show system status.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.deps import get_cache, get_claude, get_config

if TYPE_CHECKING:
    from app.config import Settings
    from app.services.cache import CacheService
    from app.services.claude import ClaudeService

logger = logging.getLogger(__name__)
router = APIRouter()


class ServiceStatus(BaseModel):
    """Health status for a single service."""

    name: str
    healthy: bool
    latency_ms: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Complete system health response."""

    status: str  # "ok" | "degraded" | "unhealthy"
    version: str
    environment: str
    timestamp: str
    services: list[ServiceStatus]


@router.get("/health", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_config),
    claude: ClaudeService = Depends(get_claude),
    cache: CacheService = Depends(get_cache),
) -> HealthResponse:
    """
    Deep health check — verifies all external dependencies.

    Returns 200 even if some services are degraded (with status="degraded").
    Returns overall status based on which services are healthy.
    """
    services: list[ServiceStatus] = []

    # Check Redis
    import time

    start = time.monotonic()
    try:
        redis_ok = await cache.health_check()
        redis_ms = (time.monotonic() - start) * 1000
        services.append(ServiceStatus(
            name="redis",
            healthy=redis_ok,
            latency_ms=round(redis_ms, 1),
            error=None if redis_ok else "Redis ping failed",
        ))
    except Exception as e:
        services.append(ServiceStatus(
            name="redis",
            healthy=False,
            error=str(e),
        ))

    # Check Claude
    start = time.monotonic()
    try:
        claude_ok = await claude.health_check()
        claude_ms = (time.monotonic() - start) * 1000
        services.append(ServiceStatus(
            name="claude",
            healthy=claude_ok,
            latency_ms=round(claude_ms, 1),
            error=None if claude_ok else "Claude API check failed",
        ))
    except Exception as e:
        services.append(ServiceStatus(
            name="claude",
            healthy=False,
            error=str(e),
        ))

    # Check Supabase (basic connectivity via REST)
    import httpx

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.supabase_url}/rest/v1/",
                headers={
                    "apikey": settings.supabase_service_role_key,
                    "Authorization": f"Bearer {settings.supabase_service_role_key}",
                },
            )
            supabase_ok = resp.status_code == 200
            supabase_ms = (time.monotonic() - start) * 1000
            services.append(ServiceStatus(
                name="supabase",
                healthy=supabase_ok,
                latency_ms=round(supabase_ms, 1),
                error=None if supabase_ok else f"HTTP {resp.status_code}",
            ))
    except Exception as e:
        services.append(ServiceStatus(
            name="supabase",
            healthy=False,
            error=str(e),
        ))

    # Derive overall status
    all_healthy = all(s.healthy for s in services)
    any_healthy = any(s.healthy for s in services)

    if all_healthy:
        status = "ok"
    elif any_healthy:
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthResponse(
        status=status,
        version=settings.app_version,
        environment=settings.environment.value,
        timestamp=datetime.now(UTC).isoformat(),
        services=services,
    )
