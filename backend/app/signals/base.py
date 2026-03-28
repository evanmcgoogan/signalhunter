"""
Signal Hunter — Signal Detector Protocol & Signal Model

Signal detectors are the deterministic Layer 2 of the system.
They consume ObservedEvents and produce Signals — scored, classified,
evidence-linked assessments of "does this matter?"

Key design principle: ALL scoring is deterministic. No LLM calls here.
Claude operates in Layer 3 (synthesis) only AFTER signals have been
scored and clustered by deterministic logic.

The composite scoring formula:
    score = evidence_strength * novelty * relevance * timeliness * source_reliability

Each factor is 0-1. The product gives a composite 0-1 score.
- Signals above `synthesis_score_threshold` (default 0.3) trigger Claude synthesis.
- Signals above `alert_score_threshold_high` (default 0.6) with 2+ evidence
  families can trigger push alerts.

Detectors are auto-discovered by the registry via subclass detection.
Adding a new detector = creating a new file with a BaseDetector subclass.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.models.types import Direction, SignalType, Urgency

if TYPE_CHECKING:
    from app.sensors.base import ObservedEvent


class Signal(BaseModel):
    """
    A scored, evidence-linked signal from a detector.

    This is the output of Layer 2 and the input to Layer 3 (synthesis).
    Every signal is traceable to the specific events that produced it.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    thesis_key: str | None = Field(
        default=None,
        description="Linked investment thesis, if applicable",
    )
    signal_type: SignalType = Field(description="Which detector produced this")
    entities: list[str] = Field(
        default_factory=list,
        description="Tickers, markets, themes this signal is about",
    )
    direction: Direction | None = Field(
        default=None,
        description="Directional bias",
    )

    # ── Scoring factors (all 0-1) ────────────────────────────────────
    evidence_strength: float = Field(
        ge=0.0, le=1.0,
        description="Move size, liquidity, confirmation count",
    )
    novelty: float = Field(
        ge=0.0, le=1.0,
        description="1.0 = completely new, 0.0 = duplicate of recent signal",
    )
    relevance: float = Field(
        ge=0.0, le=1.0,
        description="Touches active thesis, watchlist, or asset basket?",
    )
    timeliness: float = Field(
        ge=0.0, le=1.0,
        description="Leads known catalyst or downstream move?",
    )
    source_reliability: float = Field(
        ge=0.0, le=1.0,
        description="Learned from outcome tracking + user feedback",
    )

    # ── Derived ──────────────────────────────────────────────────────
    score_raw: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Composite score: product of 5 factors",
    )
    score_calibrated: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="After isotonic calibration (Phase 5)",
    )
    urgency: Urgency = Field(default=Urgency.LOW)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    # ── Evidence chain ───────────────────────────────────────────────
    evidence_event_ids: list[str] = Field(
        default_factory=list,
        description="IDs of ObservedEvents that produced this signal",
    )
    summary: str = Field(
        default="",
        description="Human-readable explanation of what was detected",
    )

    def compute_score(self) -> None:
        """
        Compute the composite score from the 5 factors.

        This is the deterministic scoring formula. No LLM involved.
        """
        self.score_raw = (
            self.evidence_strength
            * self.novelty
            * self.relevance
            * self.timeliness
            * self.source_reliability
        )
        # Calibrated score starts as raw; updated by evaluator in Phase 5
        self.score_calibrated = self.score_raw

    def compute_urgency(
        self,
        high_threshold: float = 0.6,
        medium_threshold: float = 0.3,
    ) -> None:
        """
        Derive urgency from calibrated score.

        CRITICAL is never set automatically — it requires manual override
        or 3+ evidence families with score > high_threshold.
        """
        if self.score_calibrated >= high_threshold:
            self.urgency = Urgency.HIGH
        elif self.score_calibrated >= medium_threshold:
            self.urgency = Urgency.MEDIUM
        else:
            self.urgency = Urgency.LOW


class DetectorResult(BaseModel):
    """Result from running a detector on a batch of events."""

    signals: list[Signal] = Field(default_factory=list)
    events_processed: int = 0
    detector_name: str = ""


class BaseDetector(ABC):
    """
    Abstract base class for signal detectors.

    Each detector implements one specific pattern recognition algorithm.
    It receives a batch of recent ObservedEvents and returns any signals found.

    Detectors must be:
    - Deterministic: same inputs always produce same outputs
    - Fast: no network calls, no LLM, no database writes
    - Traceable: every Signal links back to the events that triggered it
    """

    signal_type: SignalType

    @abstractmethod
    def detect(self, events: list[ObservedEvent]) -> DetectorResult:
        """
        Analyze events and return any signals found.

        This is a pure function: events in, signals out.
        No side effects. No network calls. No database access.

        Args:
            events: Recent ObservedEvents within the detection window.

        Returns:
            DetectorResult with any signals found and metadata.
        """
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__
