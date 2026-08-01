from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class GateDecision(StrEnum):
    READY_FOR_PAPER = "READY_FOR_PAPER"
    BLOCKED = "BLOCKED"
    HARD_STOP = "HARD_STOP"
    LIVE_FORBIDDEN = "LIVE_FORBIDDEN"


@dataclass(frozen=True, slots=True)
class TradingReadiness:
    symbol: str
    decision: GateDecision
    side: str | None
    risk_budget: float
    leverage: float
    checks: dict[str, bool]
    reasons: tuple[str, ...]
    evaluated_at: datetime

    @property
    def allowed(self) -> bool:
        return self.decision is GateDecision.READY_FOR_PAPER

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "decision": self.decision.value,
            "allowed": self.allowed,
            "side": self.side,
            "risk_budget": self.risk_budget,
            "leverage": self.leverage,
            "checks": self.checks,
            "reasons": list(self.reasons),
            "evaluated_at": self.evaluated_at.astimezone(UTC).isoformat(),
            "order_created": False,
            "live_execution_allowed": False,
        }
