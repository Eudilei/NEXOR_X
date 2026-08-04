from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class StrategyStatus(StrEnum):
    RESEARCH = "RESEARCH"
    PAPER = "PAPER"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


@dataclass(frozen=True, slots=True)
class StrategyDefinition:
    strategy_id: str
    name: str
    supported_regimes: tuple[str, ...]
    supported_directions: tuple[str, ...]
    status: StrategyStatus = StrategyStatus.RESEARCH
    version: str = "1.0.0"
    description: str = ""

    def supports(self, regime: str, decision: str) -> bool:
        return regime in self.supported_regimes and decision in self.supported_directions

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["supported_regimes"] = list(self.supported_regimes)
        data["supported_directions"] = list(self.supported_directions)
        return data


@dataclass(frozen=True, slots=True)
class StrategyMetric:
    strategy_id: str
    regime: str
    decision: str
    sample_count: int
    profit_factor: float
    expected_r: float
    win_rate: float
    max_drawdown_r: float
    brier_score: float | None = None
    walk_forward_pass_ratio: float | None = None
    monte_carlo_ruin_probability: float | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["updated_at"] = self.updated_at.isoformat()
        return data


@dataclass(frozen=True, slots=True)
class StrategyRanking:
    strategy_id: str
    score: float
    eligible: bool
    reasons: tuple[str, ...]
    metric: StrategyMetric

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "score": self.score,
            "eligible": self.eligible,
            "reasons": list(self.reasons),
            "metric": self.metric.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class StrategySelection:
    symbol: str
    regime: str
    decision: str
    selected_strategy_id: str | None
    rankings: tuple[StrategyRanking, ...]
    status: str
    explanation: str
    execution_allowed: bool = False
    live_certified: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "regime": self.regime,
            "decision": self.decision,
            "selected_strategy_id": self.selected_strategy_id,
            "rankings": [item.to_dict() for item in self.rankings],
            "status": self.status,
            "explanation": self.explanation,
            "execution_allowed": self.execution_allowed,
            "live_certified": self.live_certified,
            "created_at": self.created_at.isoformat(),
        }
