"""
Signal Hunter — Price Feed Sensor

Polls free price data for key assets to provide cross-asset
evidence alongside prediction market signals.

Assets tracked:
- BTC-USD, ETH-USD (crypto)
- SPY, QQQ (equity indices)
- GLD, TLT (safe havens)
- ^VIX (volatility)
- NVDA, TSLA, AAPL (mega-cap tech)

Uses Yahoo Finance chart API — free, no API key, no auth.
Events fire when an asset moves beyond MIN_PRICE_CHANGE_PCT
from its last observed price.

Phase 1.5: Crude but useful cross-asset awareness.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx

from app.models.types import Direction, EventCategory, Source
from app.sensors.base import BaseSensor, ObservedEvent, SensorHealth

logger = logging.getLogger(__name__)

# Assets to track: (yahoo symbol, display name)
TRACKED_ASSETS: list[tuple[str, str]] = [
    ("BTC-USD", "BTC"),
    ("ETH-USD", "ETH"),
    ("SPY", "SPY"),
    ("QQQ", "QQQ"),
    ("GLD", "GLD"),
    ("TLT", "TLT"),
    ("^VIX", "VIX"),
    ("NVDA", "NVDA"),
    ("TSLA", "TSLA"),
    ("AAPL", "AAPL"),
]

# Minimum % change to emit an event (absolute value)
MIN_PRICE_CHANGE_PCT = 1.5

# Yahoo Finance chart API — free, no key needed
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

# Request timeout
TIMEOUT_SECONDS = 10


class PriceFeedSensor(BaseSensor):
    """
    Polls Yahoo Finance for price changes on key assets.

    Tracks last known price per symbol. Emits ObservedEvent when
    a symbol moves more than MIN_PRICE_CHANGE_PCT from last poll.
    """

    source = Source.PRICE_FEED

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=TIMEOUT_SECONDS,
            headers={
                "User-Agent": "Mozilla/5.0 (Signal Hunter/0.1)",
            },
        )
        # Last known prices: symbol -> price
        self._last_prices: dict[str, float] = {}

    async def poll(self) -> list[ObservedEvent]:
        """Poll all tracked assets and emit events for significant moves."""
        events: list[ObservedEvent] = []

        for symbol, display_name in TRACKED_ASSETS:
            try:
                price = await self._fetch_price(symbol)
                if price is None:
                    continue

                event = self._process_price(
                    symbol, display_name, price,
                )
                if event:
                    events.append(event)

            except Exception:
                logger.warning(
                    "Price fetch failed for %s", symbol, exc_info=True,
                )

        logger.info(
            "PriceFeed poll: %d assets checked, %d events",
            len(TRACKED_ASSETS),
            len(events),
        )
        return events

    async def health_check(self) -> SensorHealth:
        """Check if Yahoo Finance API is reachable."""
        try:
            price = await self._fetch_price("SPY")
            return SensorHealth(
                source=self.source,
                healthy=price is not None,
                last_poll_at=datetime.now(UTC),
                last_event_count=0,
            )
        except Exception as e:
            return SensorHealth(
                source=self.source,
                healthy=False,
                error=str(e),
            )

    async def close(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()

    async def _fetch_price(self, symbol: str) -> float | None:
        """
        Fetch current price for a symbol from Yahoo Finance.

        Returns the regular market price, or None on failure.
        """
        try:
            resp = await self._client.get(
                YAHOO_CHART_URL.format(symbol=symbol),
                params={
                    "interval": "1d",
                    "range": "2d",
                },
            )

            if resp.status_code != 200:
                logger.warning(
                    "Yahoo Finance %s: HTTP %d",
                    symbol, resp.status_code,
                )
                return None

            data = resp.json()
            result = data.get("chart", {}).get("result")
            if not result:
                return None

            meta = result[0].get("meta", {})
            price = meta.get("regularMarketPrice")
            if price is None:
                return None

            return float(price)

        except httpx.TimeoutException:
            logger.warning("Yahoo Finance timeout for %s", symbol)
            return None

    def _process_price(
        self,
        symbol: str,
        display_name: str,
        current_price: float,
    ) -> ObservedEvent | None:
        """
        Compare current price to last known price.
        Emit event if change exceeds threshold.
        """
        last_price = self._last_prices.get(symbol)
        self._last_prices[symbol] = current_price

        # First observation — store and skip
        if last_price is None:
            return None

        # Calculate percentage change
        if last_price == 0:
            return None

        pct_change = ((current_price - last_price) / last_price) * 100

        if abs(pct_change) < MIN_PRICE_CHANGE_PCT:
            return None

        # Determine direction
        if pct_change > 0:
            direction = Direction.BULLISH
        elif pct_change < 0:
            direction = Direction.BEARISH
        else:
            direction = Direction.NEUTRAL

        # Magnitude: abs pct change, capped at 100
        magnitude = min(abs(pct_change), 100.0)

        # Reliability based on asset type
        reliability = self._asset_reliability(symbol)

        now = datetime.now(UTC)
        time_bucket = now.strftime("%Y%m%d%H")

        return ObservedEvent(
            occurred_at=now,
            source=Source.PRICE_FEED,
            source_ref=f"price:{display_name}:{time_bucket}",
            category=EventCategory.PRICE_MOVE,
            entities=[display_name],
            direction=direction,
            magnitude=magnitude,
            reliability=reliability,
            summary=(
                f"{display_name}: {pct_change:+.2f}% "
                f"(${last_price:,.2f} -> ${current_price:,.2f})"
            ),
        )

    @staticmethod
    def _asset_reliability(symbol: str) -> float:
        """
        Assign reliability based on asset liquidity/maturity.

        Higher reliability = more liquid, regulated, or well-established.
        """
        high_reliability = {"SPY", "QQQ", "GLD", "TLT", "^VIX"}
        medium_reliability = {"AAPL", "NVDA", "TSLA"}
        # Crypto gets lower reliability (more volatile, less regulated)

        if symbol in high_reliability:
            return 0.8
        if symbol in medium_reliability:
            return 0.7
        return 0.5  # Crypto
