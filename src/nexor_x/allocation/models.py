from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class AllocationCandidate:
    strategy_id: str
    symbol: str
    direction: str
    score: float
    expected_r: float
    profit_factor: float
    walk_forward_pass_ratio: float
    monte_carlo_ruin_probability: float
    max_drawdown_r: float
    current_drawdown_pct: float = 0.0
    correlation_group: str = "DEFAULT"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AllocationResult:
    strategy_id: str
    symbol: str
    direction: str
    target_weight: float
    risk_budget_pct: float
    eligible: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reasons"] = list(self.reasons)
        return data


@dataclass(frozen=True, slots=True)
class AllocationPlan:
    status: str
    allocations: tuple[AllocationResult, ...]
    total_weight: float
    total_risk_budget_pct: float
    unallocated_weight: float
    explanation: str
    execution_allowed: bool = False
    live_certified: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "allocations": [item.to_dict() for item in self.allocations],
            "total_weight": self.total_weight,
            "total_risk_budget_pct": self.total_risk_budget_pct,
            "unallocated_weight": self.unallocated_weight,
            "explanation": self.explanation,
            "execution_allowed": self.execution_allowed,
            "live_certified": self.live_certified,
            "created_at": self.created_at.isoformat(),
        }
