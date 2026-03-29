"""
Signal Hunter — Market-Aware Scheduler

Manages sensor polling using APScheduler with market-aware timing:
- Active mode (market hours): full polling speed
- Watch mode (extended hours): reduced frequency
- Sleep mode (overnight/weekends): prediction markets + curated only

The scheduler runs inside the FastAPI process (no external broker).
This is correct for a single-instance app on Railway.

Full pipeline loop per cycle:
  1. Poll sensors → ingest events (Layer 1)
  2. Query recent events → run detectors → store signals (Layer 2)
  3. If signals meet threshold → Claude synthesis → store implications (Layer 3)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.pipeline import IngestionPipeline
from app.core.synthesis import synthesize_signals
from app.models.event import EventRow
from app.models.implication import ImplicationRow
from app.models.signal import SignalRow
from app.models.types import MarketMode
from app.sensors.base import ObservedEvent
from app.sensors.kalshi import KalshiSensor
from app.sensors.polymarket import PolymarketSensor
from app.sensors.price_feed import PriceFeedSensor
from app.signals.registry import DetectorRegistry

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.config import Settings
    from app.services.cache import CacheService
    from app.services.claude import ClaudeService

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")


def get_market_mode() -> MarketMode:
    """
    Determine current market mode based on Eastern Time.

    Active: Mon-Fri 9:30 AM - 4:00 PM ET
    Watch:  Mon-Fri 4:00 AM - 9:30 AM, 4:00 PM - 8:00 PM ET
    Sleep:  Everything else (overnight, weekends)
    """
    now_et = datetime.now(ET)
    weekday = now_et.weekday()  # 0=Monday, 6=Sunday
    hour = now_et.hour
    minute = now_et.minute

    # Weekends → Sleep
    if weekday >= 5:
        return MarketMode.SLEEP

    # Market hours → Active
    if (hour == 9 and minute >= 30) or (10 <= hour < 16):
        return MarketMode.ACTIVE

    # Extended hours → Watch
    if (4 <= hour < 9) or (hour == 9 and minute < 30) or (16 <= hour < 20):
        return MarketMode.WATCH

    # Overnight → Sleep
    return MarketMode.SLEEP


def get_poll_interval_seconds() -> int:
    """Get polling interval based on current market mode."""
    mode = get_market_mode()
    if mode == MarketMode.ACTIVE:
        return 60  # Every minute during market hours
    if mode == MarketMode.WATCH:
        return 300  # Every 5 minutes during extended hours
    return 900  # Every 15 minutes overnight/weekends


class SensorScheduler:
    """
    Manages the full pipeline lifecycle: ingest → detect → synthesize.

    Creates sensors, wraps them in a pipeline, and provides
    a `run_cycle` method that APScheduler calls on interval.
    """

    # Minimum score for a signal batch to trigger synthesis
    SYNTHESIS_SCORE_THRESHOLD = 0.02

    def __init__(
        self,
        cache: CacheService,
        session_factory: async_sessionmaker[AsyncSession],
        claude: ClaudeService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._cache = cache
        self._session_factory = session_factory
        self._claude = claude
        self._settings = settings

        # Initialize sensors
        self._polymarket = PolymarketSensor()
        self._kalshi = KalshiSensor()
        self._price_feed = PriceFeedSensor()

        self._pipeline = IngestionPipeline(
            sensors=[self._polymarket, self._kalshi, self._price_feed],
            cache=cache,
        )

        # Initialize detector registry
        self._registry = DetectorRegistry()

        self._cycle_count = 0
        self._last_mode = get_market_mode()

    async def run_cycle(self) -> None:
        """
        Execute one full pipeline cycle: ingest → detect → synthesize.

        Called by APScheduler on the configured interval.
        Opens its own database session (scheduler runs outside request context).
        """
        mode = get_market_mode()
        if mode != self._last_mode:
            logger.info("Market mode changed: %s → %s", self._last_mode.value, mode.value)
            self._last_mode = mode

        self._cycle_count += 1
        logger.info(
            "Pipeline cycle #%d [mode=%s]",
            self._cycle_count,
            mode.value,
        )

        async with self._session_factory() as db:
            try:
                # ── Layer 1: Ingest events ──────────────────────────
                result = await self._pipeline.run_cycle(db)
                await db.commit()
                logger.info(
                    "Cycle #%d ingest: %d stored, %d dupes, %d errors",
                    self._cycle_count,
                    result.events_stored,
                    result.duplicates_filtered,
                    len(result.errors),
                )

                # ── Layer 2: Detect signals ─────────────────────────
                signals = await self._run_detection(db)

                # ── Layer 3: Synthesize (if we have Claude + signals) ─
                if signals and self._claude:
                    await self._run_synthesis(db, signals)

            except Exception:
                logger.exception("Pipeline cycle #%d failed", self._cycle_count)
                await db.rollback()

    async def _run_detection(self, db: AsyncSession) -> list:
        """
        Query recent events, run detectors, store signals.
        Returns list of Signal objects for synthesis.
        """
        from app.models.types import Direction as DirEnum

        # Fetch recent events from DB
        window = (
            self._settings.detection_window_minutes
            if self._settings
            else 360
        )
        cutoff = datetime.now(UTC) - timedelta(minutes=window)
        stmt = (
            select(EventRow)
            .where(EventRow.occurred_at >= cutoff)
            .order_by(EventRow.occurred_at.desc())
        )
        rows = (await db.execute(stmt)).scalars().all()

        if not rows:
            logger.info("No recent events for detection")
            return []

        # Convert EventRows → ObservedEvents for detector consumption
        from app.models.types import EventCategory, Source

        observed: list[ObservedEvent] = []
        for row in rows:
            try:
                observed.append(ObservedEvent(
                    id=row.id,
                    occurred_at=row.occurred_at,
                    ingested_at=row.ingested_at,
                    source=Source(row.source),
                    source_ref=row.source_ref,
                    category=EventCategory(row.category),
                    entities=row.entities or [],
                    thesis_key=row.thesis_key,
                    direction=DirEnum(row.direction) if row.direction else None,
                    magnitude=row.magnitude or 0.0,
                    reliability=row.reliability or 1.0,
                    novelty_hash=row.novelty_hash or "",
                    summary=row.summary or "",
                ))
            except Exception:
                logger.warning("Failed to convert EventRow %s", row.id)

        logger.info("Running detectors on %d recent events", len(observed))
        raw_signals = self._registry.run_all(observed)

        if not raw_signals:
            logger.info("No signals detected")
            return []

        # ── Novelty suppression ─────────────────────────────────
        signals = []
        suppressed = 0
        for signal in raw_signals:
            signal.compute_fingerprint()
            cooldown = (
                self._settings.signal_cooldown_seconds
                if self._settings else 1800
            )
            score_delta = (
                self._settings.signal_min_score_delta
                if self._settings else 0.05
            )
            evidence_delta = (
                self._settings.signal_min_evidence_delta
                if self._settings else 2
            )
            should_fire, reason = self._cache.check_signal_novelty(
                fingerprint=signal.fingerprint,
                score=signal.score_calibrated,
                evidence_count=len(signal.evidence_event_ids),
                cooldown_seconds=cooldown,
                min_score_delta=score_delta,
                min_evidence_delta=evidence_delta,
            )
            if should_fire:
                signals.append(signal)
                logger.info(
                    "Signal ACCEPTED [%s]: %s | %s",
                    signal.fingerprint[:8],
                    reason,
                    signal.summary[:60],
                )
            else:
                suppressed += 1
                logger.info(
                    "Signal SUPPRESSED [%s]: %s | %s",
                    signal.fingerprint[:8],
                    reason,
                    signal.summary[:60],
                )

        if suppressed:
            logger.info(
                "Novelty filter: %d accepted, %d suppressed "
                "out of %d raw signals",
                len(signals),
                suppressed,
                len(raw_signals),
            )

        if not signals:
            logger.info("All signals suppressed by novelty filter")
            return []

        # Store signals in database
        stored = 0
        for signal in signals:
            signal_row = SignalRow(
                id=signal.id,
                detected_at=signal.detected_at,
                signal_type=signal.signal_type.value,
                entities=signal.entities,
                direction=signal.direction.value if signal.direction else None,
                thesis_key=signal.thesis_key,
                evidence_strength=signal.evidence_strength,
                novelty=signal.novelty,
                relevance=signal.relevance,
                timeliness=signal.timeliness,
                source_reliability=signal.source_reliability,
                score_raw=signal.score_raw,
                score_calibrated=signal.score_calibrated,
                urgency=signal.urgency.value,
                confidence=signal.confidence,
                fingerprint=signal.fingerprint,
                evidence_event_ids=signal.evidence_event_ids,
                summary=signal.summary,
            )
            db.add(signal_row)
            stored += 1

        await db.commit()
        logger.info("Stored %d signals (top score: %.4f)", stored, signals[0].score_calibrated)
        return signals

    async def _run_synthesis(self, db: AsyncSession, signals: list) -> None:
        """
        Run Claude synthesis on signals that meet the threshold.
        Store the resulting implication.
        """
        # Filter to signals above synthesis threshold
        worthy = [s for s in signals if s.score_calibrated >= self.SYNTHESIS_SCORE_THRESHOLD]
        if not worthy:
            logger.info(
                "No signals above synthesis threshold (%.3f)",
                self.SYNTHESIS_SCORE_THRESHOLD,
            )
            return

        logger.info("Synthesizing %d signals via Claude", len(worthy))

        result = await synthesize_signals(worthy, self._claude)
        if not result:
            logger.warning("Synthesis returned no result")
            return

        # Collect all evidence event IDs from the signals
        all_event_ids = []
        for s in worthy:
            all_event_ids.extend(s.evidence_event_ids)

        # Collect all entities
        all_entities = list({e for s in worthy for e in s.entities})

        # Store implication
        impl = ImplicationRow(
            headline=result["headline"],
            summary=result["summary"],
            implications=result.get("implications", []),
            urgency=result.get("urgency", "low"),
            stance=result.get("stance", "neutral"),
            confidence=0.5,
            entities=all_entities,
            signal_ids=[s.id for s in worthy],
            event_ids=list(set(all_event_ids)),
            model_used=self._claude._synthesis_model if self._claude else "",
        )
        db.add(impl)
        await db.commit()

        logger.info(
            "Implication stored: [%s] %s",
            impl.urgency,
            impl.headline,
        )

    async def shutdown(self) -> None:
        """Clean up sensor resources."""
        await self._polymarket.close()
        await self._kalshi.close()
        await self._price_feed.close()
        logger.info("Sensor scheduler shut down")
