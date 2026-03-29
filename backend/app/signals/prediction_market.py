"""
Signal Hunter — Prediction Market Signal Detector

Detects significant probability shifts in prediction markets.
This is the Phase 1 initial wedge — prediction markets as the
primary signal source.

Signal patterns:
1. Large single-move: >10% probability shift in one poll cycle
2. Sustained drift: >15% cumulative shift over 4+ poll cycles
3. Volume spike: market volume 3x+ above its baseline
4. Cross-market correlation: multiple prediction markets moving
   in the same direction on related topics
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.models.types import Direction, EventCategory, SignalType, Source
from app.signals.base import BaseDetector, DetectorResult, Signal

if TYPE_CHECKING:
    from app.sensors.base import ObservedEvent

logger = logging.getLogger(__name__)

# Thresholds
LARGE_MOVE_MAGNITUDE = 10.0  # 10% probability shift
SIGNIFICANT_MOVE_MAGNITUDE = 7.0  # 7% — still noteworthy
MIN_RELIABILITY = 0.3  # Minimum source reliability to consider


class PredictionMarketDetector(BaseDetector):
    """
    Detects signals from prediction market price movements.

    Deterministic: same events in → same signals out. No LLM, no network calls.
    """

    signal_type = SignalType.PRICE_VELOCITY

    def detect(self, events: list[ObservedEvent]) -> DetectorResult:
        """
        Analyze prediction market events for significant patterns.

        Patterns detected:
        1. Large move: single event with magnitude > threshold
        2. Cluster move: multiple events on same entity in short window
        """
        # Filter to prediction market events only
        pred_events = [
            e for e in events
            if e.category == EventCategory.PREDICTION_MOVE
            and e.source in (Source.POLYMARKET, Source.KALSHI)
            and e.reliability >= MIN_RELIABILITY
        ]

        if not pred_events:
            return DetectorResult(
                signals=[],
                events_processed=len(events),
                detector_name=self.name,
            )

        signals: list[Signal] = []

        # Pattern 1: Large single moves
        for event in pred_events:
            if event.magnitude >= LARGE_MOVE_MAGNITUDE:
                signal = self._create_large_move_signal(event)
                signals.append(signal)
            elif event.magnitude >= SIGNIFICANT_MOVE_MAGNITUDE:
                signal = self._create_significant_move_signal(event)
                signals.append(signal)

        # Pattern 2: Cross-market correlation
        # Group events by direction, look for multiple markets moving same way
        cross_signals = self._detect_cross_market(pred_events)
        signals.extend(cross_signals)

        return DetectorResult(
            signals=signals,
            events_processed=len(events),
            detector_name=self.name,
        )

    def _create_large_move_signal(self, event: ObservedEvent) -> Signal:
        """Create a signal from a large prediction market move."""
        # Evidence strength scales with magnitude (10→0.5, 20→0.7, 30+→0.9)
        evidence = min(0.3 + (event.magnitude / 50), 0.9)

        signal = Signal(
            signal_type=SignalType.PRICE_VELOCITY,
            entities=event.entities,
            direction=event.direction,
            thesis_key=event.thesis_key,
            evidence_strength=evidence,
            novelty=0.9,  # Large moves are inherently novel
            relevance=0.7,  # Prediction markets have baseline relevance
            timeliness=0.9,  # Real-time data
            source_reliability=event.reliability,
            evidence_event_ids=[event.id],
            summary=f"Large prediction market move: {event.summary}",
        )
        signal.compute_score()
        signal.compute_urgency()
        return signal

    def _create_significant_move_signal(self, event: ObservedEvent) -> Signal:
        """Create a signal from a significant (but not large) move."""
        evidence = min(0.2 + (event.magnitude / 50), 0.7)

        signal = Signal(
            signal_type=SignalType.PRICE_VELOCITY,
            entities=event.entities,
            direction=event.direction,
            thesis_key=event.thesis_key,
            evidence_strength=evidence,
            novelty=0.7,
            relevance=0.6,
            timeliness=0.9,
            source_reliability=event.reliability,
            evidence_event_ids=[event.id],
            summary=f"Prediction market shift: {event.summary}",
        )
        signal.compute_score()
        signal.compute_urgency()
        return signal

    def _detect_cross_market(self, events: list[ObservedEvent]) -> list[Signal]:
        """
        Detect when multiple prediction markets move in the same direction.

        This is the "cross-platform" pattern: if both Polymarket AND Kalshi
        move bullish on similar topics, that's higher conviction.
        """
        signals: list[Signal] = []

        # Group by direction
        bullish = [e for e in events if e.direction == Direction.BULLISH]
        bearish = [e for e in events if e.direction == Direction.BEARISH]

        # Check for multi-source alignment
        for direction_events in [bullish, bearish]:
            if len(direction_events) < 2:
                continue

            sources = {e.source for e in direction_events}
            if len(sources) < 2:
                continue  # Need events from different sources

            # Cross-source correlation — this is a strong signal
            all_entities = []
            all_ids = []
            total_magnitude = 0.0
            for e in direction_events:
                all_entities.extend(e.entities)
                all_ids.append(e.id)
                total_magnitude += e.magnitude

            avg_magnitude = total_magnitude / len(direction_events)
            direction = direction_events[0].direction

            signal = Signal(
                signal_type=SignalType.CROSS_PLATFORM,
                entities=list(set(all_entities)),
                direction=direction,
                evidence_strength=min(0.5 + (avg_magnitude / 50), 0.9),
                novelty=0.95,  # Cross-platform correlation is very novel
                relevance=0.8,  # Multiple sources agreeing = high relevance
                timeliness=0.9,
                source_reliability=0.8,  # Cross-validation boosts reliability
                evidence_event_ids=all_ids,
                summary=(
                    f"Cross-platform prediction market alignment: "
                    f"{len(direction_events)} markets moving "
                    f"{direction.value if direction else 'together'} "
                    f"across {len(sources)} platforms"
                ),
            )
            signal.compute_score()
            signal.compute_urgency()
            signals.append(signal)

        return signals
