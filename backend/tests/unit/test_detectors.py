"""
Tests for signal detectors.

All detectors must be deterministic: same inputs → same outputs.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.types import Direction, EventCategory, SignalType, Source
from app.sensors.base import ObservedEvent
from app.signals.prediction_market import PredictionMarketDetector
from app.signals.registry import DetectorRegistry


class TestPredictionMarketDetector:
    """Tests for the prediction market signal detector."""

    def _make_event(
        self,
        *,
        magnitude: float = 15.0,
        direction: Direction = Direction.BULLISH,
        source: Source = Source.POLYMARKET,
        reliability: float = 0.7,
        entities: list[str] | None = None,
    ) -> ObservedEvent:
        return ObservedEvent(
            occurred_at=datetime.now(UTC),
            source=source,
            source_ref=f"test:{datetime.now(UTC).timestamp()}",
            category=EventCategory.PREDICTION_MOVE,
            entities=entities or ["poly:test-market"],
            direction=direction,
            magnitude=magnitude,
            reliability=reliability,
            summary=f"Test event: {magnitude}% move",
        )

    def test_large_move_produces_signal(self) -> None:
        detector = PredictionMarketDetector()
        event = self._make_event(magnitude=15.0)
        result = detector.detect([event])

        assert len(result.signals) == 1
        signal = result.signals[0]
        assert signal.signal_type == SignalType.PRICE_VELOCITY
        assert signal.direction == Direction.BULLISH
        assert signal.score_raw > 0
        assert len(signal.evidence_event_ids) == 1
        assert signal.evidence_event_ids[0] == event.id

    def test_significant_move_produces_signal(self) -> None:
        detector = PredictionMarketDetector()
        event = self._make_event(magnitude=8.0)
        result = detector.detect([event])

        assert len(result.signals) == 1
        signal = result.signals[0]
        assert signal.score_raw > 0

    def test_small_move_no_signal(self) -> None:
        detector = PredictionMarketDetector()
        event = self._make_event(magnitude=3.0)
        result = detector.detect([event])

        assert len(result.signals) == 0

    def test_low_reliability_filtered(self) -> None:
        detector = PredictionMarketDetector()
        event = self._make_event(magnitude=15.0, reliability=0.1)
        result = detector.detect([event])

        assert len(result.signals) == 0

    def test_non_prediction_events_ignored(self) -> None:
        detector = PredictionMarketDetector()
        event = ObservedEvent(
            occurred_at=datetime.now(UTC),
            source=Source.NEWS,
            source_ref="test:news",
            category=EventCategory.NEWS_HEADLINE,
            entities=["AAPL"],
            magnitude=50.0,
            summary="News event",
        )
        result = detector.detect([event])
        assert len(result.signals) == 0

    def test_cross_market_correlation(self) -> None:
        """When both Polymarket and Kalshi move same direction → cross-platform signal."""
        detector = PredictionMarketDetector()
        poly_event = self._make_event(
            source=Source.POLYMARKET, magnitude=10.0, direction=Direction.BULLISH
        )
        kalshi_event = self._make_event(
            source=Source.KALSHI, magnitude=10.0, direction=Direction.BULLISH
        )
        result = detector.detect([poly_event, kalshi_event])

        # Should have: 2 individual signals + 1 cross-platform signal
        types = [s.signal_type for s in result.signals]
        assert SignalType.CROSS_PLATFORM in types
        assert SignalType.PRICE_VELOCITY in types

    def test_deterministic(self) -> None:
        """Same inputs must produce same outputs."""
        detector = PredictionMarketDetector()
        event = self._make_event(magnitude=15.0)

        result1 = detector.detect([event])
        result2 = detector.detect([event])

        assert len(result1.signals) == len(result2.signals)
        assert result1.signals[0].score_raw == result2.signals[0].score_raw

    def test_score_increases_with_magnitude(self) -> None:
        detector = PredictionMarketDetector()
        small = self._make_event(magnitude=10.0)
        large = self._make_event(magnitude=30.0)

        result_small = detector.detect([small])
        result_large = detector.detect([large])

        assert result_large.signals[0].score_raw > result_small.signals[0].score_raw


class TestDetectorRegistry:
    """Tests for the detector registry."""

    def test_registry_initializes(self) -> None:
        registry = DetectorRegistry()
        assert len(registry.detector_names) > 0

    def test_registry_runs_all_detectors(self) -> None:
        registry = DetectorRegistry()
        event = ObservedEvent(
            occurred_at=datetime.now(UTC),
            source=Source.POLYMARKET,
            source_ref="test:registry",
            category=EventCategory.PREDICTION_MOVE,
            entities=["poly:test"],
            direction=Direction.BULLISH,
            magnitude=15.0,
            reliability=0.7,
            summary="Test event for registry",
        )
        signals = registry.run_all([event])
        assert len(signals) >= 1

    def test_registry_sorts_by_score(self) -> None:
        registry = DetectorRegistry()
        events = [
            ObservedEvent(
                occurred_at=datetime.now(UTC),
                source=Source.POLYMARKET,
                source_ref=f"test:sort:{i}",
                category=EventCategory.PREDICTION_MOVE,
                entities=["poly:test"],
                direction=Direction.BULLISH,
                magnitude=float(10 + i * 5),
                reliability=0.7,
                summary=f"Test event {i}",
            )
            for i in range(3)
        ]
        signals = registry.run_all(events)
        if len(signals) >= 2:
            assert signals[0].score_calibrated >= signals[1].score_calibrated
