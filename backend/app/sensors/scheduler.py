"""
Signal Hunter — Market-Aware Scheduler

Manages sensor polling using APScheduler with market-aware timing:
- Active mode (market hours): full polling speed
- Watch mode (extended hours): reduced frequency
- Sleep mode (overnight/weekends): prediction markets + curated only

The scheduler runs inside the FastAPI process (no external broker).
This is correct for a single-instance app on Railway.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from app.core.pipeline import IngestionPipeline
from app.models.types import MarketMode
from app.sensors.kalshi import KalshiSensor
from app.sensors.polymarket import PolymarketSensor

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.services.cache import CacheService

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
    Manages the sensor polling lifecycle.

    Creates sensors, wraps them in a pipeline, and provides
    a `run_cycle` method that APScheduler calls on interval.
    """

    def __init__(
        self,
        cache: CacheService,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._cache = cache
        self._session_factory = session_factory

        # Initialize sensors
        self._polymarket = PolymarketSensor()
        self._kalshi = KalshiSensor()

        self._pipeline = IngestionPipeline(
            sensors=[self._polymarket, self._kalshi],
            cache=cache,
        )

        self._cycle_count = 0
        self._last_mode = get_market_mode()

    async def run_cycle(self) -> None:
        """
        Execute one polling cycle.

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
                result = await self._pipeline.run_cycle(db)
                await db.commit()
                logger.info(
                    "Cycle #%d complete: %d stored, %d dupes, %d errors",
                    self._cycle_count,
                    result.events_stored,
                    result.duplicates_filtered,
                    len(result.errors),
                )
            except Exception:
                logger.exception("Pipeline cycle #%d failed", self._cycle_count)
                await db.rollback()

    async def shutdown(self) -> None:
        """Clean up sensor resources."""
        await self._polymarket.close()
        await self._kalshi.close()
        logger.info("Sensor scheduler shut down")
