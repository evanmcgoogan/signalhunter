"""
Signal Hunter — Synthesis Engine (Layer 3)

Takes scored signals from Layer 2 and produces Claude-synthesized
implication cards. This is the "what happened, why it matters, what
are the implications" layer.

Design principles:
- Claude NEVER originates scores (Layer 2 did that)
- Claude explains and narrates AFTER deterministic decisions are made
- All outputs use structured JSON (parsed, not hoped-for)
- Every synthesis call is logged with token usage

Phase 1: Crude but working — proves the full loop
Phase 4: Full world model integration + sophisticated prompts
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.claude import ClaudeService
    from app.signals.base import Signal

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = """\
You are an intelligence analyst for a sophisticated individual investor.
Your role is to synthesize market signals into actionable implications.

Be direct. Be opinionated. Connect everything back to markets and investments.

RULES:
- You are narrating signals that have already been scored by deterministic algorithms
- Do NOT invent new scores or confidence levels
- Explain WHY these signals matter, not just WHAT happened
- Be concise: the user is busy and wants the insight, not the filler
- When multiple signals align, highlight the convergence
- Always note what could invalidate the thesis

Respond ONLY with valid JSON matching this schema:
{
    "headline": "Short, punchy headline (max 100 chars)",
    "summary": "2-3 sentence explanation of what's happening and why it matters",
    "implications": ["Specific implication 1", "Specific implication 2", "Specific implication 3"],
    "stance": "bullish|bearish|cautious|neutral",
    "urgency": "low|medium|high",
    "confidence_note": "Brief note on confidence level and what could change the picture"
}"""


def _build_synthesis_prompt(signals: list[Signal]) -> str:
    """Build the user prompt from a batch of signals."""
    signal_descriptions = []
    for i, signal in enumerate(signals, 1):
        desc = (
            f"Signal {i}:\n"
            f"  Type: {signal.signal_type.value}\n"
            f"  Score: {signal.score_calibrated:.3f} (raw: {signal.score_raw:.3f})\n"
            f"  Urgency: {signal.urgency.value}\n"
            f"  Direction: {signal.direction.value if signal.direction else 'undetermined'}\n"
            f"  Entities: {', '.join(signal.entities)}\n"
            f"  Evidence: {len(signal.evidence_event_ids)} supporting events\n"
            f"  Summary: {signal.summary}\n"
        )
        signal_descriptions.append(desc)

    return (
        f"## Signal Batch ({len(signals)} signals)\n"
        f"Timestamp: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        + "\n".join(signal_descriptions)
        + "\n\nSynthesize these signals into a single implication card."
    )


async def synthesize_signals(
    signals: list[Signal],
    claude: ClaudeService,
) -> dict | None:
    """
    Synthesize a batch of signals into an implication card via Claude.

    Returns parsed JSON dict on success, None on failure.
    This is the crude Phase 1 version — it works, it's not fancy.
    """
    if not signals:
        return None

    prompt = _build_synthesis_prompt(signals)

    try:
        raw_response = await claude.synthesize(
            system_prompt=SYNTHESIS_SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=1024,
            temperature=0.3,
        )

        # Parse the JSON response
        # Strip markdown fences if Claude adds them (it shouldn't with structured prompts,
        # but V1 taught us to be defensive)
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            # Remove ```json ... ``` wrapper
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        result = json.loads(cleaned)

        # Validate required fields
        required = {"headline", "summary", "implications", "stance", "urgency"}
        if not required.issubset(result.keys()):
            missing = required - set(result.keys())
            logger.warning("Synthesis response missing fields: %s", missing)
            return None

        logger.info("Synthesis complete: %s", result.get("headline", "?"))
        return result

    except json.JSONDecodeError:
        logger.exception("Failed to parse synthesis response as JSON")
        return None
    except Exception:
        logger.exception("Synthesis failed")
        return None
