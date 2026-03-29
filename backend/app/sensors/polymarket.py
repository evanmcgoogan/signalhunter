"""
Signal Hunter — Polymarket Sensor

Polls Polymarket's CLOB (Central Limit Order Book) API for:
- Market price changes (probability shifts)
- Volume spikes
- New markets

The Polymarket API is free, no API key required.
Docs: https://docs.polymarket.com/

We use the Gamma Markets API for market metadata and the CLOB API
for real-time pricing. The key signal is *probability movement* —
when a prediction market's price moves significantly, it reflects
a real shift in collective expectations.

Normalization:
- magnitude = abs(price_change) * 100 (a 10% probability shift = magnitude 10)
- direction = BULLISH if price went up (outcome more likely), BEARISH if down
- entities = market slug + any ticker/theme tags we can extract
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.models.types import Direction, EventCategory, Source
from app.sensors.base import BaseSensor, ObservedEvent, SensorHealth

logger = logging.getLogger(__name__)

# Polymarket API endpoints
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"

# Market categories we care about (financial, geopolitical, economic)
RELEVANT_TAGS = frozenset({
    "politics", "economics", "crypto", "finance", "fed",
    "interest-rates", "inflation", "recession", "geopolitics",
    "war", "trade", "tariffs", "regulation", "elections",
    "technology", "ai", "energy", "oil", "commodities",
})

# Minimum probability change to be worth ingesting (5%)
MIN_PRICE_CHANGE = 0.05

# How many markets to fetch per poll
MARKETS_LIMIT = 100


class PolymarketSensor(BaseSensor):
    """
    Sensor for Polymarket prediction markets.

    Polls active markets for price changes and volume spikes.
    No API key required — fully public data.
    """

    source = Source.POLYMARKET

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._last_prices: dict[str, float] = {}  # condition_id → last_price
        self._last_poll_at: datetime | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=10.0,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def poll(self) -> list[ObservedEvent]:
        """
        Poll Polymarket for price changes.

        Strategy:
        1. Fetch active markets from Gamma API
        2. Compare current prices to last-known prices
        3. Emit events for significant price changes
        4. Update last-known prices
        """
        client = await self._get_client()
        events: list[ObservedEvent] = []

        try:
            markets = await self._fetch_active_markets(client)
        except Exception:
            logger.exception("Failed to fetch Polymarket markets")
            return events

        for market in markets:
            try:
                new_events = self._process_market(market)
                events.extend(new_events)
            except Exception:
                logger.exception("Failed to process market: %s", market.get("question", "?"))

        self._last_poll_at = datetime.now(UTC)
        logger.info("Polymarket poll: %d markets checked, %d events", len(markets), len(events))
        return events

    async def health_check(self) -> SensorHealth:
        """Check if Polymarket API is reachable."""
        try:
            client = await self._get_client()
            resp = await client.get(
                f"{GAMMA_API}/markets",
                params={"limit": 1, "active": True},
            )
            healthy = resp.status_code == 200
            return SensorHealth(
                source=self.source,
                healthy=healthy,
                last_poll_at=self._last_poll_at,
                last_event_count=0,
                error=None if healthy else f"HTTP {resp.status_code}",
            )
        except Exception as e:
            return SensorHealth(
                source=self.source,
                healthy=False,
                error=str(e),
            )

    async def _fetch_active_markets(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """
        Fetch active markets from Polymarket's Gamma API.

        We sort by volume (most liquid first) and filter to relevant categories.
        """
        resp = await client.get(
            f"{GAMMA_API}/markets",
            params={
                "limit": MARKETS_LIMIT,
                "active": True,
                "closed": False,
                "order": "volume",
                "ascending": False,
            },
        )
        resp.raise_for_status()
        markets = resp.json()

        # Filter to markets we care about (or return all if no tags to filter)
        return [m for m in markets if self._is_relevant(m)]

    def _is_relevant(self, market: dict[str, Any]) -> bool:
        """Check if a market is relevant to our signal universe."""
        # Always include high-volume markets
        volume = float(market.get("volume", 0) or 0)
        if volume > 1_000_000:
            return True

        # Check tags
        tags = set(market.get("tags", []) or [])
        if tags & RELEVANT_TAGS:
            return True

        # Check question text for financial keywords
        question = (market.get("question") or "").lower()
        financial_keywords = {"fed", "rate", "inflation", "gdp", "recession", "tariff",
                              "bitcoin", "btc", "eth", "oil", "gold", "spy", "nasdaq",
                              "stock", "market", "election", "president"}
        return any(kw in question for kw in financial_keywords)

    def _process_market(self, market: dict[str, Any]) -> list[ObservedEvent]:
        """
        Compare current market price to last known and emit events for changes.

        A Polymarket "market" can have multiple outcomes (conditions).
        We track each condition's price separately.
        """
        events: list[ObservedEvent] = []
        condition_id = market.get("conditionId") or market.get("condition_id", "")
        question = market.get("question", "Unknown market")
        slug = market.get("slug", condition_id)

        # Get current price (outcome token price, 0-1)
        # outcomePrices is a JSON string like "[0.65, 0.35]" for YES/NO
        outcome_prices_raw = market.get("outcomePrices")
        if not outcome_prices_raw:
            return events

        try:
            if isinstance(outcome_prices_raw, str):
                import json
                outcome_prices = json.loads(outcome_prices_raw)
            else:
                outcome_prices = outcome_prices_raw
            current_price = float(outcome_prices[0])  # YES token price
        except (ValueError, IndexError, TypeError):
            return events

        # Compare to last known price
        last_price = self._last_prices.get(condition_id)
        self._last_prices[condition_id] = current_price

        if last_price is None:
            # First time seeing this market — no delta to report
            return events

        price_change = current_price - last_price
        if abs(price_change) < MIN_PRICE_CHANGE:
            return events

        # Significant price change — create an event
        volume = float(market.get("volume", 0) or 0)
        magnitude = min(abs(price_change) * 100, 100.0)  # 10% change = magnitude 10

        direction = Direction.BULLISH if price_change > 0 else Direction.BEARISH

        event = ObservedEvent(
            occurred_at=datetime.now(UTC),
            source=Source.POLYMARKET,
            source_ref=f"poly:{condition_id}:{datetime.now(UTC).strftime('%Y%m%d%H%M')}",
            category=EventCategory.PREDICTION_MOVE,
            entities=[f"poly:{slug}"],
            direction=direction,
            magnitude=magnitude,
            reliability=self._reliability_from_volume(volume),
            summary=(
                f"Polymarket: \"{question}\" moved {price_change:+.1%} "
                f"to {current_price:.1%} (vol: ${volume:,.0f})"
            ),
        )
        event.novelty_hash = event.compute_novelty_hash()

        events.append(event)
        return events

    def _reliability_from_volume(self, volume: float) -> float:
        """
        Higher volume = more reliable signal.

        $0 volume = 0.3 reliability
        $100K volume = 0.5 reliability
        $1M volume = 0.7 reliability
        $10M+ volume = 0.9 reliability
        """
        if volume >= 10_000_000:
            return 0.9
        if volume >= 1_000_000:
            return 0.7
        if volume >= 100_000:
            return 0.5
        return 0.3

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
