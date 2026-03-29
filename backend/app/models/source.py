"""
Signal Hunter — Curated Source ORM Model

Curated sources are the "taste" layer — X accounts, YouTube channels,
podcasts that Evan curates. Each source gets sector/theme tags that
help Claude weight relevance.

Source scores are learned over time: which sources produce signals
that lead to accurate forecasts?

This table is a "durable asset" — the curation graph persists.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SourceRow(Base):
    """A curated intelligence source (X account, YouTube channel, etc.)."""

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # ── Identity ───────────────────────────────────────────────────
    source_type: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # "x_account" | "youtube" | "podcast" | "rss"
    handle: Mapped[str] = mapped_column(
        String(256), nullable=False, unique=True
    )  # @username or channel URL
    display_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    # ── Classification ─────────────────────────────────────────────
    themes: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list
    )  # ["macro", "tech", "energy"]
    sectors: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list
    )  # ["technology", "energy", "defense"]
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # ── Status ─────────────────────────────────────────────────────
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_polled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_event_count: Mapped[int] = mapped_column(default=0)

    # ── Learned quality score (Phase 5) ────────────────────────────
    quality_score: Mapped[float] = mapped_column(Float, default=0.5)
    total_events: Mapped[int] = mapped_column(default=0)
    useful_events: Mapped[int] = mapped_column(default=0)

    def __repr__(self) -> str:
        return (
            f"<Source {self.source_type}:{self.handle} "
            f"active={self.active} quality={self.quality_score:.2f}>"
        )
