"""
Signal Hunter — Signals API

GET /api/signals — scored signals from Layer 2 detectors.
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
from app.models.signal import SignalRow

router = APIRouter(prefix="/api")


class SignalResponse(BaseModel):
    """Single signal in API response."""

    id: str
    detected_at: str
    signal_type: str
    entities: list[str]
    direction: str | None
    score_raw: float
    score_calibrated: float
    urgency: str
    confidence: float
    evidence_event_ids: list[str]
    summary: str


class SignalsListResponse(BaseModel):
    """Paginated signals list."""

    signals: list[SignalResponse]
    total: int
    page: int
    page_size: int


@router.get("/signals", response_model=SignalsListResponse)
async def list_signals(
    db: AsyncSession = Depends(get_db),
    signal_type: str | None = Query(None),
    min_score: float | None = Query(None, ge=0, le=1),
    urgency: str | None = Query(None),
    hours: int = Query(24, ge=1, le=168),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> SignalsListResponse:
    """List recent signals, newest first."""
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    query = select(SignalRow).where(SignalRow.detected_at >= cutoff)

    if signal_type:
        query = query.where(SignalRow.signal_type == signal_type)
    if min_score is not None:
        query = query.where(SignalRow.score_calibrated >= min_score)
    if urgency:
        query = query.where(SignalRow.urgency == urgency)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(desc(SignalRow.detected_at)).offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.scalars().all()

    signals = [
        SignalResponse(
            id=row.id,
            detected_at=row.detected_at.isoformat(),
            signal_type=row.signal_type,
            entities=row.entities or [],
            direction=row.direction,
            score_raw=row.score_raw,
            score_calibrated=row.score_calibrated,
            urgency=row.urgency,
            confidence=row.confidence,
            evidence_event_ids=row.evidence_event_ids or [],
            summary=row.summary,
        )
        for row in rows
    ]

    return SignalsListResponse(
        signals=signals,
        total=total,
        page=page,
        page_size=page_size,
    )
