"""
Tests for the ingestion pipeline.

Tests the deduplication and event processing logic.
Database operations are not tested here (that's integration tests).
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.pipeline import PipelineResult


class TestPipelineResult:
    """Tests for PipelineResult."""

    def test_default_values(self) -> None:
        result = PipelineResult()
        assert result.total_events == 0
        assert result.novel_events == 0
        assert result.events_stored == 0
        assert result.duplicates_filtered == 0
        assert result.events_by_source == {}
        assert result.errors == []
        assert result.completed_at is None

    def test_to_dict(self) -> None:
        result = PipelineResult()
        result.total_events = 10
        result.novel_events = 8
        result.events_stored = 7
        result.duplicates_filtered = 2
        result.completed_at = datetime(2026, 3, 28, tzinfo=UTC)

        d = result.to_dict()
        assert d["total_events"] == 10
        assert d["novel_events"] == 8
        assert d["events_stored"] == 7
        assert d["duplicates_filtered"] == 2
        assert d["completed_at"] is not None


class TestSchedulerModes:
    """Tests for market-aware scheduling."""

    def test_get_poll_interval(self) -> None:
        from app.sensors.scheduler import get_poll_interval_seconds

        # Just verify it returns a positive integer
        interval = get_poll_interval_seconds()
        assert isinstance(interval, int)
        assert interval > 0
