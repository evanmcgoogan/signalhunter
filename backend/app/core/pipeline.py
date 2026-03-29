"""
Signal Hunter — Ingestion Pipeline

The pipeline is the orchestrator: it runs sensors, stores events,
runs signal detection, and (when thresholds are met) triggers synthesis.

Principle 7: end-to-end before depth. This is the crude-but-working
pipeline that proves the full loop:
    sensor.poll() → store events → detect signals → synthesize

Phase 1: Crude pipeline (top N events → Claude summary)
Phase 2: Real signal detection (detectors → clusters → synthesis)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.models.event import EventRow

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.sensors.base import BaseSensor, ObservedEvent
    from app.services.cache import CacheService

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Orchestrates the sensor → event → signal pipeline.

    Usage:
        pipeline = IngestionPipeline(sensors, cache, db_session)
        result = await pipeline.run_cycle()
    """

    def __init__(
        self,
        sensors: list[BaseSensor],
        cache: CacheService,
    ) -> None:
        self._sensors = sensors
        self._cache = cache

    async def run_cycle(self, db: AsyncSession) -> PipelineResult:
        """
        Run one full ingestion cycle:
        1. Poll all sensors
        2. Deduplicate via novelty hash
        3. Store new events
        4. Return results for signal detection (Phase 2)
        """
        result = PipelineResult()
        all_events: list[ObservedEvent] = []

        # Step 1: Poll all sensors
        for sensor in self._sensors:
            try:
                events = await sensor.poll()
                all_events.extend(events)
                result.events_by_source[sensor.source.value] = len(events)
                logger.info(
                    "Sensor %s returned %d events", sensor.source.value, len(events)
                )
            except Exception:
                logger.exception("Sensor %s failed", sensor.source.value)
                result.errors.append(f"{sensor.source.value}: poll failed")

        # Step 2: Deduplicate via novelty hash + cooling window
        novel_events: list[ObservedEvent] = []
        for event in all_events:
            if not event.novelty_hash:
                event.novelty_hash = event.compute_novelty_hash()

            if self._cache.is_novel(event.novelty_hash, cooling_minutes=30):
                novel_events.append(event)
            else:
                result.duplicates_filtered += 1

        # Step 3: Store new events in database
        stored = 0
        for event in novel_events:
            try:
                stored += await self._store_event(db, event)
            except Exception:
                logger.exception("Failed to store event %s", event.source_ref)
                result.errors.append(f"store failed: {event.source_ref}")

        await db.flush()
        result.events_stored = stored
        result.total_events = len(all_events)
        result.novel_events = len(novel_events)
        result.completed_at = datetime.now(UTC)

        logger.info(
            "Pipeline cycle: %d total, %d novel, %d stored, %d dupes, %d errors",
            result.total_events,
            result.novel_events,
            result.events_stored,
            result.duplicates_filtered,
            len(result.errors),
        )

        return result

    async def _store_event(self, db: AsyncSession, event: ObservedEvent) -> int:
        """
        Store an event in the database.

        Uses INSERT ... ON CONFLICT DO NOTHING for idempotent ingestion.
        Returns 1 if stored, 0 if duplicate (by source_ref).
        """
        # Also store the raw payload in Redis if we have one
        if event.payload_ref:
            # Raw payload was already stored by the sensor — nothing extra needed
            pass

        row = EventRow(
            id=event.id,
            occurred_at=event.occurred_at,
            ingested_at=event.ingested_at,
            source=event.source.value,
            source_ref=event.source_ref,
            category=event.category.value,
            entities=event.entities,
            thesis_key=event.thesis_key,
            direction=event.direction.value if event.direction else None,
            magnitude=event.magnitude,
            reliability=event.reliability,
            novelty_hash=event.novelty_hash,
            summary=event.summary,
            payload_ref=event.payload_ref,
        )

        # Use merge to handle potential conflicts gracefully
        # The unique constraint on source_ref prevents true duplicates
        try:
            db.add(row)
            await db.flush()
            return 1
        except Exception:
            await db.rollback()
            # Try ON CONFLICT DO NOTHING approach
            stmt = text("""
                INSERT INTO events (
                    id, occurred_at, ingested_at, source, source_ref, category,
                    entities, thesis_key, direction, magnitude, reliability,
                    novelty_hash, summary, payload_ref
                ) VALUES (
                    :id, :occurred_at, :ingested_at, :source, :source_ref, :category,
                    :entities, :thesis_key, :direction, :magnitude, :reliability,
                    :novelty_hash, :summary, :payload_ref
                ) ON CONFLICT (source_ref) DO NOTHING
            """)
            await db.execute(stmt, {
                "id": row.id,
                "occurred_at": row.occurred_at,
                "ingested_at": row.ingested_at,
                "source": row.source,
                "source_ref": row.source_ref,
                "category": row.category,
                "entities": row.entities,
                "thesis_key": row.thesis_key,
                "direction": row.direction,
                "magnitude": row.magnitude,
                "reliability": row.reliability,
                "novelty_hash": row.novelty_hash,
                "summary": row.summary,
                "payload_ref": row.payload_ref,
            })
            return 0


class PipelineResult:
    """Result of one pipeline cycle."""

    def __init__(self) -> None:
        self.total_events: int = 0
        self.novel_events: int = 0
        self.events_stored: int = 0
        self.duplicates_filtered: int = 0
        self.events_by_source: dict[str, int] = {}
        self.errors: list[str] = []
        self.completed_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "total_events": self.total_events,
            "novel_events": self.novel_events,
            "events_stored": self.events_stored,
            "duplicates_filtered": self.duplicates_filtered,
            "events_by_source": self.events_by_source,
            "errors": self.errors,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
