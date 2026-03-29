"""
Signal Hunter — Forecast & Outcome ORM Models

Forecasts are directional predictions extracted from implications.
Outcomes are the actual results, graded by the evaluator (Phase 5).

Together they form the evaluation loop — the mechanism that makes
Signal Hunter get better over time.

These tables are "durable assets" — they persist across rewrites.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ForecastRow(Base):
    """A directional prediction extracted from an implication."""

    __tablename__ = "forecasts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # ── What was predicted ─────────────────────────────────────────
    entities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    magnitude_expected: Mapped[float | None] = mapped_column(Float, nullable=True)
    timeframe_hours: Mapped[float] = mapped_column(Float, nullable=False, default=24.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # ── Provenance ─────────────────────────────────────────────────
    implication_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    signal_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # ── Resolution ─────────────────────────────────────────────────
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    outcome_direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    outcome_magnitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    grade_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        status = self.grade or "pending"
        return (
            f"<Forecast id={self.id[:8]}… {self.direction} "
            f"conf={self.confidence:.2f} status={status}>"
        )
