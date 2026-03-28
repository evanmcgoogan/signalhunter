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
