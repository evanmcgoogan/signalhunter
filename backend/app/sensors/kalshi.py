"""
Signal Hunter — Kalshi Sensor

Polls Kalshi's public API for prediction market price changes.
Kalshi is a CFTC-regulated prediction market — higher reliability
than unregulated alternatives.

API docs: https://trading-api.readme.io/reference/getevents

The free tier gives us market listings and prices. We don't need
trading access — just observation.

Key signal: probability movement on economic/political markets.
Kalshi specializes in regulated event contracts: Fed rates, CPI,
unemployment, elections, etc.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.models.types import Direction, EventCategory, Source
from app.sensors.base import BaseSensor, ObservedEvent, SensorHealth

logger = logging.getLogger(__name__)

KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"

# Categories worth monitoring
RELEVANT_CATEGORIES = frozenset({
    "Economics", "Fed", "Finance", "Politics",
    "Climate", "Technology", "Crypto",
})

MIN_PRICE_CHANGE = 5  # Kalshi prices are in cents (0-100)


class KalshiSensor(BaseSensor):
    """
    Sensor for Kalshi prediction markets.

    Kalshi uses a cents-based pricing system (0-100) where the price
    represents the market's probability estimate. A YES contract at 65
    means the market thinks there's a 65% chance.
    """

    source = Source.KALSHI

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._last_prices: dict[str, int] = {}  # market_ticker → last_yes_price
        self._last_poll_at: datetime | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=10.0,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def poll(self) -> list[ObservedEvent]:
        """
        Poll Kalshi for market price changes.

        1. Fetch active markets
        2. Compare to last-known prices
        3. Emit events for significant changes
        """
        client = await self._get_client()
        events: list[ObservedEvent] = []

        try:
            markets = await self._fetch_markets(client)
        except Exception:
            logger.exception("Failed to fetch Kalshi markets")
            return events

        for market in markets:
            try:
                new_events = self._process_market(market)
                events.extend(new_events)
            except Exception:
                logger.exception(
                    "Failed to process Kalshi market: %s", market.get("ticker", "?")
                )

        self._last_poll_at = datetime.now(UTC)
        logger.info("Kalshi poll: %d markets checked, %d events", len(markets), len(events))
        return events

    async def health_check(self) -> SensorHealth:
        """Check if Kalshi API is reachable."""
        try:
            client = await self._get_client()
            resp = await client.get(
                f"{KALSHI_API}/events",
                params={"limit": 1, "status": "open"},
            )
            healthy = resp.status_code == 200
            return SensorHealth(
                source=self.source,
                healthy=healthy,
                last_poll_at=self._last_poll_at,
                error=None if healthy else f"HTTP {resp.status_code}",
            )
        except Exception as e:
            return SensorHealth(
                source=self.source,
                healthy=False,
                error=str(e),
            )

    async def _fetch_markets(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch active Kalshi markets."""
        resp = await client.get(
            f"{KALSHI_API}/markets",
            params={
                "limit": 100,
                "status": "open",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        markets = data.get("markets", [])

        return [m for m in markets if self._is_relevant(m)]

    def _is_relevant(self, market: dict[str, Any]) -> bool:
        """Filter to financially relevant markets."""
        category = market.get("category", "")
        if category in RELEVANT_CATEGORIES:
            return True

        # Check title for financial keywords
        title = (market.get("title") or "").lower()
        keywords = {"fed", "rate", "cpi", "inflation", "gdp", "unemployment",
                     "recession", "tariff", "bitcoin", "oil", "election", "president"}
        return any(kw in title for kw in keywords)

    def _process_market(self, market: dict[str, Any]) -> list[ObservedEvent]:
        """Process a single Kalshi market for price changes."""
        events: list[ObservedEvent] = []

        ticker = market.get("ticker", "")
        title = market.get("title", "Unknown")
        yes_price = market.get("yes_bid") or market.get("last_price") or 0
        if not isinstance(yes_price, (int, float)):
            return events

        yes_price = int(yes_price)

        # Compare to last known
        last_price = self._last_prices.get(ticker)
        self._last_prices[ticker] = yes_price

        if last_price is None:
            return events

        change = yes_price - last_price
        if abs(change) < MIN_PRICE_CHANGE:
            return events

        # Significant change
        volume = int(market.get("volume", 0) or 0)
        magnitude = min(abs(change), 100.0)  # cents map directly to magnitude

        direction = Direction.BULLISH if change > 0 else Direction.BEARISH

        event = ObservedEvent(
            occurred_at=datetime.now(UTC),
            source=Source.KALSHI,
            source_ref=f"kalshi:{ticker}:{datetime.now(UTC).strftime('%Y%m%d%H%M')}",
            category=EventCategory.PREDICTION_MOVE,
            entities=[f"kalshi:{ticker}"],
            direction=direction,
            magnitude=magnitude,
            reliability=self._reliability_from_volume(volume),
            summary=(
                f"Kalshi: \"{title}\" moved {change:+d}¢ "
                f"to {yes_price}¢ (vol: {volume:,})"
            ),
        )
        event.novelty_hash = event.compute_novelty_hash()

        events.append(event)
        return events

    def _reliability_from_volume(self, volume: int) -> float:
        """Higher volume = more reliable. Kalshi is regulated so base is higher."""
        if volume >= 100_000:
            return 0.9
        if volume >= 10_000:
            return 0.7
        if volume >= 1_000:
            return 0.6
        return 0.4

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
