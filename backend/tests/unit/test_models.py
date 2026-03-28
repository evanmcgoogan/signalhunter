"""
Unit tests for core domain models.

These tests verify the foundational types and protocols that the
entire system depends on. No external services, no database, no network.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.types import (
    Direction,
    EventCategory,
    FeedbackAction,
    MarketMode,
    SignalType,
    Source,
    Stance,
    Urgency,
)
from app.sensors.base import ObservedEvent
from app.signals.base import Signal


class TestObservedEvent:
    """Tests for the ObservedEvent model."""

    def test_create_minimal_event(self) -> None:
        """An event with required fields should be valid."""
        event = ObservedEvent(
            occurred_at=datetime.now(UTC),
            source=Source.POLYMARKET,
            source_ref="poly_123",
            category=EventCategory.PREDICTION_MOVE,
            magnitude=45.0,
        )
        assert event.source == Source.POLYMARKET
        assert event.magnitude == 45.0
        assert event.id  # Auto-generated UUID
        assert event.ingested_at  # Auto-generated timestamp
        assert event.entities == []
        assert event.direction is None

    def test_create_full_event(self) -> None:
        """An event with all fields populated."""
        event = ObservedEvent(
            occurred_at=datetime(2026, 3, 28, 14, 30, tzinfo=UTC),
            source=Source.PRICE_FEED,
            source_ref="spy_20260328_143000",
            category=EventCategory.PRICE_MOVE,
            entities=["SPY", "QQQ"],
            thesis_key="fed_pivot",
            direction=Direction.BULLISH,
            magnitude=72.5,
            reliability=0.95,
            summary="SPY up 1.2% in 15 minutes on volume",
        )
        assert event.entities == ["SPY", "QQQ"]
        assert event.thesis_key == "fed_pivot"
        assert event.direction == Direction.BULLISH
        assert event.reliability == 0.95

    def test_novelty_hash_deterministic(self) -> None:
        """Same event fields should produce the same novelty hash."""
        event = ObservedEvent(
            occurred_at=datetime.now(UTC),
            source=Source.POLYMARKET,
            source_ref="poly_123",
            category=EventCategory.PREDICTION_MOVE,
            entities=["fed_rate_cut"],
            direction=Direction.BULLISH,
            magnitude=50.0,
        )
        hash1 = event.compute_novelty_hash()
        hash2 = event.compute_novelty_hash()
        assert hash1 == hash2
        assert len(hash1) == 16

    def test_novelty_hash_different_for_different_events(self) -> None:
        """Different events should produce different novelty hashes."""
        event1 = ObservedEvent(
            occurred_at=datetime.now(UTC),
            source=Source.POLYMARKET,
            source_ref="poly_123",
            category=EventCategory.PREDICTION_MOVE,
            entities=["fed_rate_cut"],
            direction=Direction.BULLISH,
            magnitude=50.0,
        )
        event2 = ObservedEvent(
            occurred_at=datetime.now(UTC),
            source=Source.KALSHI,
            source_ref="kalshi_456",
            category=EventCategory.PREDICTION_MOVE,
            entities=["trump_tariff"],
            direction=Direction.BEARISH,
            magnitude=60.0,
        )
        assert event1.compute_novelty_hash() != event2.compute_novelty_hash()

    def test_magnitude_bounds(self) -> None:
        """Magnitude must be 0-100."""
        import pytest

        with pytest.raises(Exception):  # noqa: B017
            ObservedEvent(
                occurred_at=datetime.now(UTC),
                source=Source.POLYMARKET,
                source_ref="test",
                category=EventCategory.PREDICTION_MOVE,
                magnitude=150.0,  # Invalid
            )


class TestSignal:
    """Tests for the Signal model and scoring."""

    def test_compute_score(self) -> None:
        """Composite score is the product of 5 factors."""
        signal = Signal(
            signal_type=SignalType.PRICE_VELOCITY,
            evidence_strength=0.8,
            novelty=0.9,
            relevance=0.7,
            timeliness=0.6,
            source_reliability=0.95,
        )
        signal.compute_score()

        expected = 0.8 * 0.9 * 0.7 * 0.6 * 0.95
        assert abs(signal.score_raw - expected) < 1e-10

    def test_compute_score_zero_factor(self) -> None:
        """If any factor is 0, the composite score is 0."""
        signal = Signal(
            signal_type=SignalType.VOLUME_SHOCK,
            evidence_strength=0.9,
            novelty=0.0,  # Not novel — duplicate
            relevance=0.8,
            timeliness=0.7,
            source_reliability=0.9,
        )
        signal.compute_score()
        assert signal.score_raw == 0.0

    def test_urgency_from_score(self) -> None:
        """Urgency is derived from calibrated score."""
        # 0.95^5 = 0.774 which is above the 0.6 HIGH threshold
        signal = Signal(
            signal_type=SignalType.CROSS_PLATFORM,
            evidence_strength=0.95,
            novelty=0.95,
            relevance=0.95,
            timeliness=0.95,
            source_reliability=0.95,
        )
        signal.compute_score()
        signal.compute_urgency()
        assert signal.urgency == Urgency.HIGH

    def test_low_urgency(self) -> None:
        """Low-scoring signals get LOW urgency."""
        signal = Signal(
            signal_type=SignalType.PRICE_VELOCITY,
            evidence_strength=0.3,
            novelty=0.5,
            relevance=0.4,
            timeliness=0.3,
            source_reliability=0.5,
        )
        signal.compute_score()
        signal.compute_urgency()
        assert signal.urgency == Urgency.LOW

    def test_evidence_chain(self) -> None:
        """Signals must link back to evidence events."""
        signal = Signal(
            signal_type=SignalType.BASKET_MOVE,
            evidence_strength=0.7,
            novelty=0.8,
            relevance=0.9,
            timeliness=0.6,
            source_reliability=0.85,
            evidence_event_ids=["evt_001", "evt_002", "evt_003"],
            summary="TLT, GLD, and rate prediction all moving dovish",
        )
        assert len(signal.evidence_event_ids) == 3
        assert "evt_001" in signal.evidence_event_ids


class TestEnums:
    """Verify all enum values are accessible and correct."""

    def test_sources_include_future_phases(self) -> None:
        """Source enum includes UW and curated sources for future phases."""
        assert Source.UW_OPTIONS == "uw_options"
        assert Source.UW_DARKPOOL == "uw_darkpool"
        assert Source.CURATED_X == "curated_x"
        assert Source.CURATED_YT == "curated_yt"

    def test_market_modes(self) -> None:
        assert MarketMode.ACTIVE == "active"
        assert MarketMode.WATCH == "watch"
        assert MarketMode.SLEEP == "sleep"

    def test_feedback_actions(self) -> None:
        assert FeedbackAction.USEFUL == "useful"
        assert FeedbackAction.ACTED_ON == "acted_on"

    def test_stance_values(self) -> None:
        assert Stance.CAUTIOUS == "cautious"
