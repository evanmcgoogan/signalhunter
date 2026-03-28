"""
Signal Hunter — Core Domain Types

These enums and base types are used across the entire system.
They define the vocabulary of Signal Hunter.

Design note: these are deliberately simple. They're the "nouns" of
the system. Adding a new source or signal type is a one-line enum addition,
not an architectural change.
"""

from __future__ import annotations

from enum import StrEnum


class Source(StrEnum):
    """Where data comes from. Each sensor maps to exactly one Source."""

    # Phase 1: Initial wedge
    POLYMARKET = "polymarket"
    KALSHI = "kalshi"
    PRICE_FEED = "price_feed"
    NEWS = "news"

    # Phase 3: Curated intelligence
    CURATED_X = "curated_x"
    CURATED_YT = "curated_yt"

    # Phase 7: Unusual Whales (gated)
    UW_OPTIONS = "uw_options"
    UW_DARKPOOL = "uw_darkpool"
    UW_PREDICTIONS = "uw_predictions"
    UW_NEWS = "uw_news"
    UW_CALENDAR = "uw_calendar"
    UW_CONGRESS = "uw_congress"
    UW_INSTITUTIONS = "uw_institutions"


class EventCategory(StrEnum):
    """What type of event this is."""

    PREDICTION_MOVE = "prediction_move"
    PRICE_MOVE = "price_move"
    VOLUME_SPIKE = "volume_spike"
    NEWS_HEADLINE = "news_headline"
    EXPERT_OPINION = "expert_opinion"
    TRANSCRIPT = "transcript"
    ECONOMIC_EVENT = "economic_event"
    CONGRESSIONAL_TRADE = "congressional_trade"
    OPTIONS_FLOW = "options_flow"
    DARK_POOL_PRINT = "dark_pool_print"
    INSTITUTIONAL_FILING = "institutional_filing"


class SignalType(StrEnum):
    """What kind of signal was detected."""

    PRICE_VELOCITY = "price_velocity"
    VOLUME_SHOCK = "volume_shock"
    CROSS_PLATFORM = "cross_platform"
    BASKET_MOVE = "basket_move"
    CATALYST_PROXIMITY = "catalyst_proximity"
    NO_NEWS_MOVE = "no_news_move"
    LEAD_LAG = "lead_lag"
    EXPERT_CONSENSUS = "expert_consensus"
    MULTI_SIGNAL = "multi_signal"
    OPTIONS_FLOW_UNUSUAL = "options_flow_unusual"
    DARK_POOL_LARGE = "dark_pool_large"
    CONGRESSIONAL_TIMING = "congressional_timing"


class Direction(StrEnum):
    """Directional bias."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class Urgency(StrEnum):
    """How time-sensitive this is."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Stance(StrEnum):
    """Implication stance toward affected assets."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    CAUTIOUS = "cautious"
    NEUTRAL = "neutral"


class FeedbackAction(StrEnum):
    """User feedback on an implication card."""

    USEFUL = "useful"
    NOT_USEFUL = "not_useful"
    ACTED_ON = "acted_on"
    IGNORED = "ignored"


class MarketMode(StrEnum):
    """Market-aware scheduling mode."""

    ACTIVE = "active"      # Market hours: full polling
    WATCH = "watch"        # Extended hours: reduced
    SLEEP = "sleep"        # Overnight/weekends: minimal
