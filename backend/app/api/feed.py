"""
Signal Hunter — Intelligence Feed API

GET /api/feed — Claude-synthesized implication cards.
This is the primary user-facing endpoint — the "what happened and why it matters" feed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select

from app.db import get_db

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
from app.models.implication import ImplicationRow

router = APIRouter(prefix="/api")


class ImplicationResponse(BaseModel):
    """Single implication card."""

    id: str
    created_at: str
    headline: str
    summary: str
    implications: list[str]
    urgency: str
    stance: str
    confidence: float
    entities: list[str]
    signal_ids: list[str]
    event_ids: list[str]
    world_model_updates: dict
    feedback: str | None


class FeedResponse(BaseModel):
    """Intelligence feed response."""

    items: list[ImplicationResponse]
    total: int
    page: int
    page_size: int


@router.get("/feed", response_model=FeedResponse)
async def intelligence_feed(
    db: AsyncSession = Depends(get_db),
    urgency: str | None = Query(None),
    hours: int = Query(48, ge=1, le=168),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> FeedResponse:
    """
    Intelligence feed — Claude-synthesized implication cards.

    Returns newest first. Default: last 48 hours.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    query = select(ImplicationRow).where(ImplicationRow.created_at >= cutoff)

    if urgency:
        query = query.where(ImplicationRow.urgency == urgency)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(desc(ImplicationRow.created_at)).offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.scalars().all()

    items = [
        ImplicationResponse(
            id=row.id,
            created_at=row.created_at.isoformat(),
            headline=row.headline,
            summary=row.summary,
            implications=row.implications or [],
            urgency=row.urgency,
            stance=row.stance,
            confidence=row.confidence,
            entities=row.entities or [],
            signal_ids=row.signal_ids or [],
            event_ids=row.event_ids or [],
            world_model_updates=row.world_model_updates or {},
            feedback=row.feedback,
        )
        for row in rows
    ]

    return FeedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
