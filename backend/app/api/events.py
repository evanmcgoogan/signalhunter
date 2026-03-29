"""
Signal Hunter — Events API

GET /api/events — paginated list of ingested events with filtering.
This is the raw data layer — what the sensors observed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select

from app.db import get_db
from app.models.event import EventRow

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api")


class EventResponse(BaseModel):
    """Single event in API response."""

    id: str
    occurred_at: str
    ingested_at: str
    source: str
    source_ref: str
    category: str
    entities: list[str]
    thesis_key: str | None
    direction: str | None
    magnitude: float
    reliability: float
    summary: str


class EventsListResponse(BaseModel):
    """Paginated events list."""

    events: list[EventResponse]
    total: int
    page: int
    page_size: int


@router.get("/events", response_model=EventsListResponse)
async def list_events(
    db: AsyncSession = Depends(get_db),
    source: str | None = Query(None, description="Filter by source"),
    category: str | None = Query(None, description="Filter by category"),
    entity: str | None = Query(None, description="Filter by entity (substring match)"),
    min_magnitude: float | None = Query(None, ge=0, le=100, description="Minimum magnitude"),
    hours: int = Query(24, ge=1, le=168, description="Look back N hours"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> EventsListResponse:
    """
    List recent events with optional filtering.

    Returns newest first. Default: last 24 hours.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    query = select(EventRow).where(EventRow.occurred_at >= cutoff)

    if source:
        query = query.where(EventRow.source == source)
    if category:
        query = query.where(EventRow.category == category)
    if entity:
        query = query.where(EventRow.entities.any(entity))
    if min_magnitude is not None:
        query = query.where(EventRow.magnitude >= min_magnitude)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(desc(EventRow.occurred_at)).offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.scalars().all()

    events = [
        EventResponse(
            id=row.id,
            occurred_at=row.occurred_at.isoformat(),
            ingested_at=row.ingested_at.isoformat(),
            source=row.source,
            source_ref=row.source_ref,
            category=row.category,
            entities=row.entities or [],
            thesis_key=row.thesis_key,
            direction=row.direction,
            magnitude=row.magnitude,
            reliability=row.reliability,
            summary=row.summary,
        )
        for row in rows
    ]

    return EventsListResponse(
        events=events,
        total=total,
        page=page,
        page_size=page_size,
    )
