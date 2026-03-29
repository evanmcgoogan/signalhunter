"""
Signal Hunter — Signal Detector Registry

Auto-discovers and manages all signal detectors.
Runs them against event batches and collects results.

Adding a new detector = creating a new file with a BaseDetector subclass
and importing it here. No other code changes needed.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.signals.prediction_market import PredictionMarketDetector

if TYPE_CHECKING:
    from app.sensors.base import ObservedEvent
    from app.signals.base import BaseDetector, Signal

logger = logging.getLogger(__name__)


class DetectorRegistry:
    """
    Manages all signal detectors and runs them against event batches.

    Usage:
        registry = DetectorRegistry()
        signals = registry.run_all(events)
    """

    def __init__(self) -> None:
        self._detectors: list[BaseDetector] = []
        self._register_all()

    def _register_all(self) -> None:
        """Register all available detectors."""
        # Phase 1: Prediction market detector
        self._detectors.append(PredictionMarketDetector())

        # Phase 2 (future): Add more detectors here
        # self._detectors.append(VolumeShockDetector())
        # self._detectors.append(CrossAssetDetector())
        # self._detectors.append(NoNewsMoveDetector())
        # self._detectors.append(CalendarProximityDetector())

        logger.info(
            "Detector registry initialized: %d detectors",
            len(self._detectors),
        )

    def run_all(self, events: list[ObservedEvent]) -> list[Signal]:
        """
        Run all registered detectors against the event batch.

        Returns all signals found, sorted by score (highest first).
        """
        all_signals: list[Signal] = []

        for detector in self._detectors:
            try:
                result = detector.detect(events)
                if result.signals:
                    logger.info(
                        "Detector %s found %d signals",
                        detector.name,
                        len(result.signals),
                    )
                    all_signals.extend(result.signals)
            except Exception:
                logger.exception("Detector %s failed", detector.name)

        # Sort by calibrated score, highest first
        all_signals.sort(key=lambda s: s.score_calibrated, reverse=True)

        logger.info(
            "Registry run complete: %d total signals from %d detectors",
            len(all_signals),
            len(self._detectors),
        )

        return all_signals

    @property
    def detector_names(self) -> list[str]:
        return [d.name for d in self._detectors]
