"""
Signal Hunter — Sensor Protocol & Event Model

This is the most important interface in the system.

Every data source (Polymarket, Kalshi, price feeds, news, curated X/YT,
and eventually Unusual Whales) implements the Sensor protocol. Each sensor
polls its source and returns normalized ObservedEvents.

The sensor abstraction is what makes the system extensible:
- Phase 1: Polymarket, Kalshi, price feeds, news
- Phase 3: Curated X accounts, YouTube/podcasts
- Phase 7: Unusual Whales options flow, dark pool, congress

Adding a new source = implementing one class. No other code changes.

Design decisions:
- `payload_ref` instead of storing raw JSON in the hot table. Raw payloads
  are stored compressed elsewhere and referenced by hash. This keeps the
  events table fast for queries.
- `novelty_hash` enables cooling-window deduplication. If the same signal
  fires again within the cooling window, it's downweighted, not re-alerted.
- `source_ref` is the source-specific ID for idempotent ingestion. If we
  poll the same Polymarket trade twice, the second INSERT is a no-op.
"""

from __future__ import annotations

import hashlib
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.types import Direction, EventCategory, Source  # noqa: TC001


class ObservedEvent(BaseModel):
    """
    A normalized event from any data source.

    This is the universal input to signal detection.
    Every sensor produces these; every detector consumes them.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = Field(description="When the event happened (UTC)")
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When we received it (latency tracking)",
    )
    source: Source = Field(description="Which sensor produced this")
    source_ref: str = Field(
        description="Source-specific unique ID for idempotent ingestion"
    )
    category: EventCategory = Field(description="What type of event")
    entities: list[str] = Field(
        default_factory=list,
        description="Tickers, market slugs, themes affected",
    )
    thesis_key: str | None = Field(
        default=None,
        description="Linked investment thesis, if applicable",
    )
    direction: Direction | None = Field(
        default=None,
        description="Directional bias, if determinable",
    )
    magnitude: float = Field(
        ge=0.0,
        le=100.0,
        description="Normalized 0-100: how big is this event?",
    )
    reliability: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Source reliability score (learned over time)",
    )
    novelty_hash: str = Field(
        default="",
        description="Hash for cooling-window dedup",
    )
    summary: str = Field(
        default="",
        description="Human-readable 1-liner",
    )
    payload_ref: str = Field(
        default="",
        description="Reference to compressed raw payload (not in hot table)",
    )

    def compute_novelty_hash(self, fields: list[str] | None = None) -> str:
        """
        Compute a novelty hash from key fields.

        Two events with the same novelty_hash within a cooling window
        are considered duplicates. The hash is intentionally coarse —
        we want to catch "same thing, slightly different" cases.
        """
        if fields is None:
            fields = [self.source.value, self.category.value, *sorted(self.entities)]
            if self.direction:
                fields.append(self.direction.value)
        raw = "|".join(fields)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


class SensorHealth(BaseModel):
    """Health status of a sensor."""

    source: Source
    healthy: bool
    last_poll_at: datetime | None = None
    last_event_count: int = 0
    error: str | None = None


class BaseSensor(ABC):
    """
    Abstract base class for all sensors.

    Subclass this for each data source. Implement `poll()` and
    `health_check()`. The scheduler calls `poll()` on the configured
    interval; the health endpoint calls `health_check()`.

    The `source` class variable identifies which Source enum this sensor
    produces events for. It must be set by every subclass.
    """

    source: Source

    @abstractmethod
    async def poll(self) -> list[ObservedEvent]:
        """
        Poll the data source and return normalized events.

        Returns only NEW events since last poll. Idempotency is enforced
        by source_ref — if an event with the same source_ref already exists
        in the database, the INSERT is a no-op (ON CONFLICT DO NOTHING).

        This method should:
        1. Fetch raw data from the external API
        2. Filter to only new data (using last poll timestamp or cursor)
        3. Normalize each item into an ObservedEvent
        4. Compute novelty_hash for each event
        5. Return the list

        It should NOT:
        - Write to the database (the pipeline does that)
        - Run signal detection (Layer 2 does that)
        - Call Claude (Layer 3 does that)
        """
        ...

    @abstractmethod
    async def health_check(self) -> SensorHealth:
        """
        Check if this sensor's data source is reachable and responding.

        Called by the /health endpoint. Should be fast (< 2s timeout).
        """
        ...

    def _make_payload_ref(self, raw_data: dict[str, Any]) -> str:
        """
        Create a content-addressed reference for raw payload storage.

        The raw JSON is stored compressed outside the hot events table,
        referenced by this hash. This keeps the events table lean while
        preserving full fidelity for debugging and replay.
        """
        import json

        content = json.dumps(raw_data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:32]
