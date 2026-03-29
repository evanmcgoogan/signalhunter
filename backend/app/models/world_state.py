"""
Signal Hunter — World State ORM Models

The world model is a small set of living state variables that
represent the current market regime. Updates are deterministic
(Layer 2), with Claude providing narrative only.

Two tables:
- `world_state`: Current snapshot (single row, upserted)
- `world_state_log`: Every transition (append-only audit trail)

The log is one of the "durable assets" — it persists across rewrites.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class WorldStateRow(Base):
    """
    Current world model state — single row, upserted.

    Each field is a 0-1 float with a narrative explanation.
    """

    __tablename__ = "world_state"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default="current",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # ── State variables (all 0-1 floats) ───────────────────────────
    risk_regime: Mapped[float] = mapped_column(Float, default=0.5)
    risk_regime_label: Mapped[str] = mapped_column(String(32), default="neutral")
    risk_regime_reason: Mapped[str] = mapped_column(Text, default="")

    vix_regime: Mapped[float] = mapped_column(Float, default=0.3)
    vix_regime_label: Mapped[str] = mapped_column(String(32), default="low")
    vix_regime_reason: Mapped[str] = mapped_column(Text, default="")

    geo_risk: Mapped[float] = mapped_column(Float, default=0.3)
    geo_risk_label: Mapped[str] = mapped_column(String(32), default="low")
    geo_risk_reason: Mapped[str] = mapped_column(Text, default="")

    fed_stance: Mapped[float] = mapped_column(Float, default=0.5)
    fed_stance_label: Mapped[str] = mapped_column(String(32), default="neutral")
    fed_stance_reason: Mapped[str] = mapped_column(Text, default="")

    smart_money_flow: Mapped[float] = mapped_column(Float, default=0.5)
    smart_money_flow_label: Mapped[str] = mapped_column(String(32), default="neutral")
    smart_money_flow_reason: Mapped[str] = mapped_column(Text, default="")

    sector_leader: Mapped[str] = mapped_column(String(64), default="")
    sector_leader_reason: Mapped[str] = mapped_column(Text, default="")

    next_catalyst: Mapped[str] = mapped_column(String(256), default="")
    next_catalyst_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<WorldState risk={self.risk_regime_label} updated={self.updated_at}>"


class WorldStateLogRow(Base):
    """
    Append-only audit trail of world model transitions.

    Every state change is logged with: what changed, old value, new value, why.
    This is a durable asset — it persists across code rewrites.
    """

    __tablename__ = "world_state_log"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    variable: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    old_value: Mapped[float] = mapped_column(Float, nullable=False)
    new_value: Mapped[float] = mapped_column(Float, nullable=False)
    old_label: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    new_label: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    trigger_signal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Full state snapshot at time of change
    state_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)

    def __repr__(self) -> str:
        return (
            f"<WorldStateLog {self.variable}: "
            f"{self.old_label}→{self.new_label} at {self.created_at}>"
        )
