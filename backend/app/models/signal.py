"""
Signal Hunter — Signal ORM Model

The `signals` table stores every signal produced by Layer 2 detectors.
Each signal is linked to the events that triggered it via `evidence_event_ids`.

The composite score is stored pre-computed for fast querying and sorting.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SignalRow(Base):
    """ORM model for the signals table."""

    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    signal_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    thesis_key: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # ── Scoring factors ────────────────────────────────────────────
    evidence_strength: Mapped[float] = mapped_column(Float, nullable=False)
    novelty: Mapped[float] = mapped_column(Float, nullable=False)
    relevance: Mapped[float] = mapped_column(Float, nullable=False)
    timeliness: Mapped[float] = mapped_column(Float, nullable=False)
    source_reliability: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Derived scores ─────────────────────────────────────────────
    score_raw: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score_calibrated: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    urgency: Mapped[str] = mapped_column(String(16), nullable=False, default="low")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    # ── Evidence chain ─────────────────────────────────────────────
    evidence_event_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    __table_args__ = (
        Index("ix_signals_score", "score_calibrated"),
        Index("ix_signals_urgency_detected", "urgency", "detected_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<SignalRow id={self.id[:8]}… type={self.signal_type} "
            f"score={self.score_calibrated:.3f} urgency={self.urgency}>"
        )
