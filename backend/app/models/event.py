"""
Signal Hunter — Event ORM Model

The `events` table stores every normalized observation from every sensor.
This is the "hot table" — the primary input to signal detection.

Design decisions:
- `source_ref` has a unique constraint for idempotent ingestion (ON CONFLICT DO NOTHING)
- `payload_ref` references compressed payloads stored in Redis, not inline JSONB
- `novelty_hash` enables cooling-window deduplication at the cache layer
- Partitioning by `occurred_at` can be added later if the table grows beyond
  reasonable size (unlikely for single-user in first year)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EventRow(Base):
    """ORM model for the events table."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_ref: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    thesis_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    reliability: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    novelty_hash: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    payload_ref: Mapped[str] = mapped_column(String(32), nullable=False, default="")

    __table_args__ = (
        Index("ix_events_source_occurred", "source", "occurred_at"),
        Index("ix_events_novelty", "novelty_hash"),
    )

    def __repr__(self) -> str:
        return (
            f"<EventRow id={self.id[:8]}… source={self.source} "
            f"category={self.category} magnitude={self.magnitude}>"
        )
