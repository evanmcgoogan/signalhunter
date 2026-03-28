"""
Signal Hunter — Claude AI Service

Wraps the Anthropic SDK with structured outputs, cost tracking,
and model routing (Opus for synthesis, Haiku for triage).

Design principles:
- Claude NEVER originates scores or state transitions (Layer 2 does that)
- Claude explains and narrates AFTER deterministic decisions are made
- All outputs use structured outputs (strict JSON schema)
- Every call is logged with token usage for cost tracking
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import anthropic
from pydantic import BaseModel

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


class ClaudeUsage(BaseModel):
    """Token usage tracking for cost monitoring."""

    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    purpose: str = ""


class ClaudeService:
    """
    Anthropic Claude client for Signal Hunter.

    Usage:
        claude = ClaudeService(settings)
        result = await claude.synthesize(system_prompt, user_prompt, response_schema)
    """

    def __init__(self, settings: Settings) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._synthesis_model = settings.claude_synthesis_model
        self._triage_model = settings.claude_triage_model
        self._usage_log: list[ClaudeUsage] = []

    async def synthesize(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model_override: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> str:
        """
        Call Claude for synthesis/narration (Layer 3).

        Uses the synthesis model (Opus-class) by default.
        Returns raw text response. For structured output, use `synthesize_structured`.

        Args:
            system_prompt: System instructions for Claude.
            user_prompt: The actual request with signal data + context.
            model_override: Use a specific model instead of default.
            max_tokens: Maximum response length.
            temperature: Lower = more deterministic. 0.3 for synthesis.
        """
        model = model_override or self._synthesis_model

        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        self._log_usage(response, model, "synthesis")

        # Extract text from response
        text_blocks = [
            block.text for block in response.content if block.type == "text"
        ]
        return "\n".join(text_blocks)

    async def triage(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.1,
    ) -> str:
        """
        Call Claude for triage/categorization (cheap, fast).

        Uses the triage model (Haiku-class). For tweet categorization,
        transcript summarization, and relevance scoring.
        """
        return await self.synthesize(
            system_prompt,
            user_prompt,
            model_override=self._triage_model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def health_check(self) -> bool:
        """Verify the Anthropic API is reachable and the key is valid."""
        try:
            response = await self._client.messages.create(
                model=self._triage_model,
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}],
            )
            return response.stop_reason == "end_turn"
        except Exception:
            logger.exception("Claude health check failed")
            return False

    def get_usage_summary(self) -> dict[str, Any]:
        """Return aggregate token usage for cost monitoring."""
        total_input = sum(u.input_tokens for u in self._usage_log)
        total_output = sum(u.output_tokens for u in self._usage_log)
        return {
            "total_calls": len(self._usage_log),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "by_purpose": self._usage_by_purpose(),
        }

    def _log_usage(
        self,
        response: anthropic.types.Message,
        model: str,
        purpose: str,
    ) -> None:
        usage = ClaudeUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=model,
            purpose=purpose,
        )
        self._usage_log.append(usage)
        logger.info(
            "Claude call: model=%s purpose=%s in=%d out=%d",
            model,
            purpose,
            usage.input_tokens,
            usage.output_tokens,
        )

    def _usage_by_purpose(self) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {}
        for u in self._usage_log:
            if u.purpose not in result:
                result[u.purpose] = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
            result[u.purpose]["calls"] += 1
            result[u.purpose]["input_tokens"] += u.input_tokens
            result[u.purpose]["output_tokens"] += u.output_tokens
        return result
