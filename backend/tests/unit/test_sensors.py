"""
Tests for sensor implementations.

These tests use mocked HTTP responses — no real API calls.
"""

from __future__ import annotations

from app.models.types import Direction, EventCategory, Source
from app.sensors.polymarket import PolymarketSensor


class TestPolymarketSensor:
    """Tests for the Polymarket sensor."""

    def test_source_is_polymarket(self) -> None:
        sensor = PolymarketSensor()
        assert sensor.source == Source.POLYMARKET

    def test_reliability_from_volume(self) -> None:
        sensor = PolymarketSensor()
        assert sensor._reliability_from_volume(0) == 0.3
        assert sensor._reliability_from_volume(50_000) == 0.3
        assert sensor._reliability_from_volume(100_000) == 0.5
        assert sensor._reliability_from_volume(1_000_000) == 0.7
        assert sensor._reliability_from_volume(10_000_000) == 0.9
        assert sensor._reliability_from_volume(50_000_000) == 0.9

    def test_is_relevant_high_volume(self) -> None:
        sensor = PolymarketSensor()
        market = {"volume": 2_000_000, "tags": [], "question": "Something random"}
        assert sensor._is_relevant(market) is True

    def test_is_relevant_matching_tags(self) -> None:
        sensor = PolymarketSensor()
        market = {"volume": 100, "tags": ["politics", "other"], "question": "Will X win?"}
        assert sensor._is_relevant(market) is True

    def test_is_relevant_matching_keywords(self) -> None:
        sensor = PolymarketSensor()
        market = {"volume": 100, "tags": [], "question": "Will the Fed cut rates?"}
        assert sensor._is_relevant(market) is True

    def test_is_relevant_irrelevant(self) -> None:
        sensor = PolymarketSensor()
        market = {
            "volume": 100,
            "tags": ["sports"],
            "question": "Will the Lakers win?",
        }
        assert sensor._is_relevant(market) is False

    def test_process_market_first_poll_no_events(self) -> None:
        """First poll for a market should not emit events (no baseline to compare)."""
        sensor = PolymarketSensor()
        market = {
            "conditionId": "abc123",
            "question": "Will Bitcoin hit $100K?",
            "slug": "bitcoin-100k",
            "outcomePrices": "[0.65, 0.35]",
            "volume": "500000",
        }
        events = sensor._process_market(market)
        assert len(events) == 0

    def test_process_market_small_change_filtered(self) -> None:
        """Small price changes should be filtered out."""
        sensor = PolymarketSensor()
        # First poll — sets baseline
        market = {
            "conditionId": "abc123",
            "question": "Will Bitcoin hit $100K?",
            "slug": "bitcoin-100k",
            "outcomePrices": "[0.65, 0.35]",
            "volume": "500000",
        }
        sensor._process_market(market)

        # Second poll — tiny change
        market["outcomePrices"] = "[0.66, 0.34]"  # 1% change < 5% threshold
        events = sensor._process_market(market)
        assert len(events) == 0

    def test_process_market_significant_change_emits_event(self) -> None:
        """Significant price changes should produce an event."""
        sensor = PolymarketSensor()
        # First poll
        market = {
            "conditionId": "abc123",
            "question": "Will Bitcoin hit $100K?",
            "slug": "bitcoin-100k",
            "outcomePrices": "[0.50, 0.50]",
            "volume": "1000000",
        }
        sensor._process_market(market)

        # Second poll — big move
        market["outcomePrices"] = "[0.65, 0.35]"  # 15% change > 5% threshold
        events = sensor._process_market(market)
        assert len(events) == 1

        event = events[0]
        assert event.source == Source.POLYMARKET
        assert event.category == EventCategory.PREDICTION_MOVE
        assert event.direction == Direction.BULLISH
        assert abs(event.magnitude - 15.0) < 0.01  # 0.15 * 100
        assert "poly:bitcoin-100k" in event.entities
        assert "moved" in event.summary
        assert event.novelty_hash != ""

    def test_process_market_bearish_direction(self) -> None:
        """Price drop should produce bearish direction."""
        sensor = PolymarketSensor()
        market = {
            "conditionId": "def456",
            "question": "Will there be a recession?",
            "slug": "recession-2026",
            "outcomePrices": "[0.60, 0.40]",
            "volume": "500000",
        }
        sensor._process_market(market)

        market["outcomePrices"] = "[0.45, 0.55]"  # 15% drop
        events = sensor._process_market(market)
        assert len(events) == 1
        assert events[0].direction == Direction.BEARISH


class TestKalshiSensor:
    """Tests for the Kalshi sensor."""

    def test_source_is_kalshi(self) -> None:
        from app.sensors.kalshi import KalshiSensor

        sensor = KalshiSensor()
        assert sensor.source == Source.KALSHI

    def test_reliability_from_volume(self) -> None:
        from app.sensors.kalshi import KalshiSensor

        sensor = KalshiSensor()
        assert sensor._reliability_from_volume(0) == 0.4
        assert sensor._reliability_from_volume(1_000) == 0.6
        assert sensor._reliability_from_volume(10_000) == 0.7
        assert sensor._reliability_from_volume(100_000) == 0.9

    def test_is_relevant_economics(self) -> None:
        from app.sensors.kalshi import KalshiSensor

        sensor = KalshiSensor()
        market = {"category": "Economics", "title": "CPI reading"}
        assert sensor._is_relevant(market) is True

    def test_is_relevant_keyword(self) -> None:
        from app.sensors.kalshi import KalshiSensor

        sensor = KalshiSensor()
        market = {"category": "Other", "title": "Will the Fed raise rates?"}
        assert sensor._is_relevant(market) is True

    def test_process_market_significant_change(self) -> None:
        from app.sensors.kalshi import KalshiSensor

        sensor = KalshiSensor()
        # First poll
        market = {
            "ticker": "FED-RATE-CUT",
            "title": "Fed rate cut in June",
            "yes_bid": 60,
            "volume": 5000,
        }
        sensor._process_market(market)

        # Second poll — big move
        market["yes_bid"] = 75  # 15 cent change
        events = sensor._process_market(market)
        assert len(events) == 1
        assert events[0].source == Source.KALSHI
        assert events[0].direction == Direction.BULLISH
        assert events[0].magnitude == 15.0
