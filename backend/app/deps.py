"""
Signal Hunter — Dependency Injection

Provides typed dependencies for FastAPI route handlers.
All external services are lazily instantiated on first use and
shared across requests.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.services.cache import CacheService
from app.services.claude import ClaudeService

# Module-level singletons, lazily initialized
_claude: ClaudeService | None = None
_cache: CacheService | None = None


def get_claude() -> ClaudeService:
    """Lazily initialized Claude service singleton."""
    global _claude
    if _claude is None:
        _claude = ClaudeService(get_settings())
    return _claude


def get_cache() -> CacheService:
    """Lazily initialized cache service singleton."""
    global _cache
    if _cache is None:
        _cache = CacheService(get_settings())
    return _cache


def get_config() -> Settings:
    """Settings dependency for route handlers."""
    return get_settings()
