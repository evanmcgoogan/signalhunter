"""Tests for price feed sensor and signal fingerprinting."""

from __future__ import annotations

from app.models.types import Direction, EventCategory, SignalType, Source
from app.sensors.price_feed import PriceFeedSensor
from app.signals.base import Signal


class TestPriceFeedSensor:
    """Tests for PriceFeedSensor._process_price logic."""

    def setup_method(self) -> None:
        self.sensor = PriceFeedSensor()

    def test_source_is_price_feed(self) -> None:
        assert self.sensor.source == Source.PRICE_FEED

    def test_first_poll_no_event(self) -> None:
        """First observation stores price but doesn't emit."""
        result = self.sensor._process_price("SPY", "SPY", 500.0)
        assert result is None
        assert self.sensor._last_prices["SPY"] == 500.0

    def test_small_change_no_event(self) -> None:
        """Change below threshold doesn't emit."""
        self.sensor._last_prices["SPY"] = 500.0
        result = self.sensor._process_price("SPY", "SPY", 503.0)
        assert result is None  # 0.6% < 1.5% threshold

    def test_significant_move_emits_event(self) -> None:
        """Change above threshold emits event."""
        self.sensor._last_prices["SPY"] = 500.0
        result = self.sensor._process_price("SPY", "SPY", 510.0)
        assert result is not None
        assert result.source == Source.PRICE_FEED
        assert result.category == EventCategory.PRICE_MOVE
        assert result.direction == Direction.BULLISH
        assert abs(result.magnitude - 2.0) < 0.01
        assert "SPY" in result.entities

    def test_bearish_direction(self) -> None:
        """Negative change is bearish."""
        self.sensor._last_prices["BTC-USD"] = 60000.0
        result = self.sensor._process_price("BTC-USD", "BTC", 57000.0)
        assert result is not None
        assert result.direction == Direction.BEARISH
        assert abs(result.magnitude - 5.0) < 0.01

    def test_reliability_by_asset_class(self) -> None:
        """ETFs get higher reliability than crypto."""
        assert PriceFeedSensor._asset_reliability("SPY") == 0.8
        assert PriceFeedSensor._asset_reliability("NVDA") == 0.7
        assert PriceFeedSensor._asset_reliability("BTC-USD") == 0.5

    def test_summary_format(self) -> None:
        """Summary includes symbol and price change."""
        self.sensor._last_prices["QQQ"] = 500.0
        result = self.sensor._process_price("QQQ", "QQQ", 510.0)
        assert result is not None
        assert "QQQ" in result.summary
        assert "+2.00%" in result.summary

    def test_source_ref_includes_time_bucket(self) -> None:
        """Source ref uses hourly buckets for idempotency."""
        self.sensor._last_prices["GLD"] = 400.0
        result = self.sensor._process_price("GLD", "GLD", 410.0)
        assert result is not None
        assert result.source_ref.startswith("price:GLD:")


class TestSignalFingerprint:
    """Tests for Signal.compute_fingerprint."""

    def test_same_signal_same_fingerprint(self) -> None:
        """Signals with same type/entities/direction get same fingerprint."""
        s1 = Signal(
            signal_type=SignalType.PRICE_VELOCITY,
            entities=["BTC"],
            direction=Direction.BULLISH,
            evidence_strength=0.5,
            novelty=0.5,
            relevance=0.5,
            timeliness=0.5,
            source_reliability=0.5,
        )
        s2 = Signal(
            signal_type=SignalType.PRICE_VELOCITY,
            entities=["BTC"],
            direction=Direction.BULLISH,
            evidence_strength=0.8,  # different score
            novelty=0.9,
            relevance=0.5,
            timeliness=0.5,
            source_reliability=0.5,
        )
        assert s1.compute_fingerprint() == s2.compute_fingerprint()

    def test_different_direction_different_fingerprint(self) -> None:
        """Direction change = new signal."""
        s1 = Signal(
            signal_type=SignalType.PRICE_VELOCITY,
            entities=["SPY"],
            direction=Direction.BULLISH,
            evidence_strength=0.5,
            novelty=0.5,
            relevance=0.5,
            timeliness=0.5,
            source_reliability=0.5,
        )
        s2 = Signal(
            signal_type=SignalType.PRICE_VELOCITY,
            entities=["SPY"],
            direction=Direction.BEARISH,
            evidence_strength=0.5,
            novelty=0.5,
            relevance=0.5,
            timeliness=0.5,
            source_reliability=0.5,
        )
        assert s1.compute_fingerprint() != s2.compute_fingerprint()

    def test_different_entities_different_fingerprint(self) -> None:
        """Different assets = different signal."""
        s1 = Signal(
            signal_type=SignalType.PRICE_VELOCITY,
            entities=["BTC"],
            direction=Direction.BULLISH,
            evidence_strength=0.5,
            novelty=0.5,
            relevance=0.5,
            timeliness=0.5,
            source_reliability=0.5,
        )
        s2 = Signal(
            signal_type=SignalType.PRICE_VELOCITY,
            entities=["ETH"],
            direction=Direction.BULLISH,
            evidence_strength=0.5,
            novelty=0.5,
            relevance=0.5,
            timeliness=0.5,
            source_reliability=0.5,
        )
        assert s1.compute_fingerprint() != s2.compute_fingerprint()

    def test_entity_order_irrelevant(self) -> None:
        """Entity order doesn't affect fingerprint (sorted internally)."""
        s1 = Signal(
            signal_type=SignalType.CROSS_PLATFORM,
            entities=["BTC", "ETH"],
            direction=Direction.BULLISH,
            evidence_strength=0.5,
            novelty=0.5,
            relevance=0.5,
            timeliness=0.5,
            source_reliability=0.5,
        )
        s2 = Signal(
            signal_type=SignalType.CROSS_PLATFORM,
            entities=["ETH", "BTC"],
            direction=Direction.BULLISH,
            evidence_strength=0.5,
            novelty=0.5,
            relevance=0.5,
            timeliness=0.5,
            source_reliability=0.5,
        )
        assert s1.compute_fingerprint() == s2.compute_fingerprint()

    def test_fingerprint_is_stored_on_signal(self) -> None:
        """compute_fingerprint sets the fingerprint field."""
        s = Signal(
            signal_type=SignalType.PRICE_VELOCITY,
            entities=["SPY"],
            direction=Direction.BEARISH,
            evidence_strength=0.5,
            novelty=0.5,
            relevance=0.5,
            timeliness=0.5,
            source_reliability=0.5,
        )
        fp = s.compute_fingerprint()
        assert s.fingerprint == fp
        assert len(fp) == 20
