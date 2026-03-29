"""
Signal Hunter — Cache Service (Upstash Redis)

Provides caching for:
- API response caching (reduce external API calls)
- Rate limit tracking
- Novelty hashes for cooling-window deduplication
- Raw payload storage (compressed, referenced by hash)

Uses Upstash Redis HTTP API — no persistent TCP connection needed.
Works from serverless, edge, and standard environments.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from upstash_redis import Redis

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis cache using Upstash.

    Thin wrapper that provides typed methods for Signal Hunter's
    specific caching needs.
    """

    def __init__(self, settings: Settings) -> None:
        self._redis = Redis(
            url=settings.upstash_redis_rest_url,
            token=settings.upstash_redis_rest_token,
        )

    async def health_check(self) -> bool:
        """Verify Redis is reachable."""
        try:
            result = self._redis.ping()
            return result == "PONG"
        except Exception:
            logger.exception("Redis health check failed")
            return False

    # ── General cache ────────────────────────────────────────────────

    def get(self, key: str) -> str | None:
        """Get a cached value by key."""
        result = self._redis.get(key)
        if result is None:
            return None
        return str(result)

    def set(self, key: str, value: str, *, ttl_seconds: int = 3600) -> None:
        """Set a cached value with TTL."""
        self._redis.set(key, value, ex=ttl_seconds)

    def get_json(self, key: str) -> dict[str, Any] | None:
        """Get a cached JSON object."""
        raw = self.get(key)
        if raw is None:
            return None
        return json.loads(raw)  # type: ignore[no-any-return]

    def set_json(self, key: str, value: dict[str, Any], *, ttl_seconds: int = 3600) -> None:
        """Cache a JSON-serializable object."""
        self.set(key, json.dumps(value, default=str), ttl_seconds=ttl_seconds)

    # ── Novelty dedup ────────────────────────────────────────────────

    def is_novel(self, novelty_hash: str, cooling_minutes: int = 30) -> bool:
        """
        Check if this novelty hash has been seen within the cooling window.

        Returns True if this is a NEW signal (not seen recently).
        Returns False if this is a DUPLICATE (seen within cooling window).
        """
        key = f"novelty:{novelty_hash}"
        existing = self._redis.get(key)
        if existing is not None:
            return False

        # Mark as seen with TTL = cooling window
        self._redis.set(key, "1", ex=cooling_minutes * 60)
        return True

    # ── Signal novelty suppression ─────────────────────────────────

    def check_signal_novelty(
        self,
        fingerprint: str,
        score: float,
        evidence_count: int,
        *,
        cooldown_seconds: int = 1800,
        min_score_delta: float = 0.05,
        min_evidence_delta: int = 2,
    ) -> tuple[bool, str]:
        """
        Check whether a signal with this fingerprint should fire.

        Returns (should_fire, reason) where reason explains the decision.

        A signal is suppressed if a signal with the same fingerprint
        was seen recently AND:
        - score hasn't increased by min_score_delta
        - evidence count hasn't grown by min_evidence_delta

        Re-fires when:
        - First time seeing this fingerprint
        - Score materially increased
        - Evidence family expanded
        - Cooldown expired (natural re-evaluation)
        """
        key = f"sig_novelty:{fingerprint}"
        existing = self.get_json(key)

        if existing is None:
            # First time — always fire
            self._store_signal_novelty(
                key, score, evidence_count, cooldown_seconds,
            )
            return True, "new_signal"

        last_score = existing.get("score", 0.0)
        last_evidence = existing.get("evidence_count", 0)
        times_suppressed = existing.get("times_suppressed", 0)

        score_delta = score - last_score
        evidence_delta = evidence_count - last_evidence

        # Check if score materially increased
        if score_delta >= min_score_delta:
            self._store_signal_novelty(
                key, score, evidence_count, cooldown_seconds,
            )
            return True, (
                f"score_increase: {last_score:.4f} -> {score:.4f} "
                f"(+{score_delta:.4f})"
            )

        # Check if evidence family expanded
        if evidence_delta >= min_evidence_delta:
            self._store_signal_novelty(
                key, score, evidence_count, cooldown_seconds,
            )
            return True, (
                f"evidence_expanded: {last_evidence} -> "
                f"{evidence_count} (+{evidence_delta})"
            )

        # Suppress — same thesis, no meaningful change
        self._redis.set(
            key,
            json.dumps({
                "score": last_score,
                "evidence_count": last_evidence,
                "times_suppressed": times_suppressed + 1,
                "first_seen": existing.get("first_seen", ""),
                "last_seen": datetime.now(UTC).isoformat(),
            }),
            ex=cooldown_seconds,
        )
        return False, (
            f"suppressed (x{times_suppressed + 1}): "
            f"score_delta={score_delta:+.4f} "
            f"evidence_delta={evidence_delta:+d}"
        )

    def _store_signal_novelty(
        self,
        key: str,
        score: float,
        evidence_count: int,
        ttl_seconds: int,
    ) -> None:
        """Store/update signal novelty state."""
        existing = self.get_json(key)
        first_seen = (
            existing.get("first_seen", "")
            if existing
            else datetime.now(UTC).isoformat()
        )
        self._redis.set(
            key,
            json.dumps({
                "score": score,
                "evidence_count": evidence_count,
                "times_suppressed": 0,
                "first_seen": first_seen,
                "last_seen": datetime.now(UTC).isoformat(),
            }),
            ex=ttl_seconds,
        )

    # ── Rate limiting ────────────────────────────────────────────────

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Simple sliding window rate limiter.

        Returns True if the request is allowed, False if rate limited.
        """
        full_key = f"ratelimit:{key}"
        current = self._redis.get(full_key)
        count = int(current) if current is not None else 0

        if count >= max_requests:
            return False

        pipe = self._redis.pipeline()
        pipe.incr(full_key)
        if count == 0:
            pipe.expire(full_key, window_seconds)
        pipe.exec()
        return True

    # ── Raw payload storage ──────────────────────────────────────────

    def store_payload(self, payload_ref: str, raw_data: dict[str, Any]) -> None:
        """
        Store a raw API response payload, referenced by content hash.

        TTL is 30 days (hot retention policy).
        """
        key = f"payload:{payload_ref}"
        self.set_json(key, raw_data, ttl_seconds=30 * 24 * 3600)

    def get_payload(self, payload_ref: str) -> dict[str, Any] | None:
        """Retrieve a stored raw payload by reference."""
        return self.get_json(f"payload:{payload_ref}")
