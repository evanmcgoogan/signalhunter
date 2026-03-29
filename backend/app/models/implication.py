"""
Signal Hunter — Implication ORM Model

Implications are the output of Layer 3 (Claude synthesis).
They represent "what happened, why it matters, what to do about it."

Each implication is linked to the signal cluster that triggered it
and tracks user feedback for the learning loop (Phase 5).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ImplicationRow(Base):
    """ORM model for the implications table (Claude synthesis output)."""

    __tablename__ = "implications"

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

    # ── Content ────────────────────────────────────────────────────
    headline: Mapped[str] = mapped_column(String(256), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    implications: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)

    # ── Classification ─────────────────────────────────────────────
    urgency: Mapped[str] = mapped_column(String(16), nullable=False, default="low")
    stance: Mapped[str] = mapped_column(String(16), nullable=False, default="neutral")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    entities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # ── Evidence chain ─────────────────────────────────────────────
    signal_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    event_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # ── World model updates ────────────────────────────────────────
    world_model_updates: Mapped[dict] = mapped_column(JSONB, default=dict)

    # ── Claude metadata ────────────────────────────────────────────
    model_used: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)

    # ── User feedback (Phase 5) ────────────────────────────────────
    feedback: Mapped[str | None] = mapped_column(String(16), nullable=True)
    feedback_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<ImplicationRow id={self.id[:8]}… "
            f"urgency={self.urgency} headline={self.headline[:40]}…>"
        )
