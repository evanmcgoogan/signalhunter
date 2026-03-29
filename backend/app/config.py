"""
Signal Hunter — Application Configuration

All configuration is loaded from environment variables via Pydantic Settings.
No config.json, no hardcoded secrets, no magic. Every setting has a type,
a default (where safe), and is validated at startup.

Signal thresholds are ported from V1's config.py dataclasses but use
Pydantic for validation and environment variable binding.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the .env file path relative to the project root
# backend/app/config.py → backend/ → Signal Hunter/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Environment(StrEnum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All secrets come from .env (gitignored). In production, they come
    from Railway/Vercel environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────
    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"
    app_name: str = "Signal Hunter"
    app_version: str = "0.1.0"

    # ── Anthropic (Claude API) ───────────────────────────────────────
    anthropic_api_key: str = Field(description="Anthropic API key for Claude")

    # Models — we pin specific versions for reproducibility
    claude_synthesis_model: str = "claude-sonnet-4-20250514"
    claude_triage_model: str = "claude-sonnet-4-20250514"

    # ── Supabase ─────────────────────────────────────────────────────
    supabase_url: str = Field(description="Supabase project URL")
    supabase_anon_key: str = Field(description="Supabase anon (public) key")
    supabase_service_role_key: str = Field(description="Supabase service role key")

    # ── Upstash Redis ────────────────────────────────────────────────
    upstash_redis_rest_url: str = Field(description="Upstash Redis REST URL")
    upstash_redis_rest_token: str = Field(description="Upstash Redis REST token")

    # ── Twilio (optional, SMS alerts) ────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    twilio_to_number: str = ""

    # ── Future: Unusual Whales (Phase 7) ─────────────────────────────
    uw_api_key: str = ""

    # ── Future: TwitterAPI.io (Phase 3) ──────────────────────────────
    twitter_api_io_key: str = ""

    # ── Database (Supabase Postgres via asyncpg) ────────────────────
    # postgresql+asyncpg://postgres.[ref]:[pwd]@aws-0-[region].pooler.supabase.com:6543/postgres
    database_url: str = ""

    # ── Signal Thresholds (ported from V1) ───────────────────────────
    # These are the deterministic scoring parameters.
    # Tunable without code changes via environment variables.
    price_velocity_min_change: float = 5.0
    price_velocity_time_window_minutes: int = 30
    volume_shock_multiplier: float = 3.0
    volume_baseline_hours: int = 24
    cross_market_divergence_threshold: float = 8.0
    alert_score_threshold: float = 40.0

    # ── Polling ──────────────────────────────────────────────────────
    poll_interval_seconds: int = 60
    full_refresh_interval_minutes: int = 15

    # ── Alert Budget ─────────────────────────────────────────────────
    max_push_alerts_per_day: int = 3
    max_false_positives_per_day: int = 1
    min_evidence_families_for_alert: int = 2

    # ── Synthesis ────────────────────────────────────────────────────
    synthesis_score_threshold: float = 0.3
    alert_score_threshold_high: float = 0.6

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            msg = f"log_level must be one of {valid}, got '{v}'"
            raise ValueError(msg)
        return upper

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def has_twilio(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token)

    @property
    def has_unusual_whales(self) -> bool:
        return bool(self.uw_api_key)

    @property
    def has_twitter(self) -> bool:
        return bool(self.twitter_api_io_key)


def _load_env() -> None:
    """Load .env file into os.environ at module import time."""
    from dotenv import load_dotenv

    if _ENV_FILE.exists():
        load_dotenv(_ENV_FILE, override=True)


# Load .env BEFORE any Settings construction
_load_env()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached settings singleton.

    Call this from dependency injection, not by importing a global.
    The .env file is already loaded into os.environ by _load_env() above.
    """
    return Settings()  # type: ignore[call-arg]
