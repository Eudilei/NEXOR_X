from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class OutcomeObservation:
    symbol: str
    decision: str
    raw_edge: float
    regime: str
    realized_r: float
    closed_at: datetime

    @property
    def won(self) -> bool:
        return self.realized_r > 0.0


@dataclass(frozen=True, slots=True)
class CalibrationEstimate:
    ready: bool
    sample_count: int
    win_probability: float | None
    expected_r: float | None
    profit_factor: float | None
    brier_score: float | None
    lower_edge: float
    upper_edge: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "sample_count": self.sample_count,
            "win_probability": self.win_probability,
            "expected_r": self.expected_r,
            "profit_factor": self.profit_factor,
            "brier_score": self.brier_score,
            "lower_edge": self.lower_edge,
            "upper_edge": self.upper_edge,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class WalkForwardFold:
    fold: int
    train_count: int
    test_count: int
    expected_r: float | None
    realized_r: float
    profit_factor: float | None
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "fold": self.fold,
            "train_count": self.train_count,
            "test_count": self.test_count,
            "expected_r": self.expected_r,
            "realized_r": self.realized_r,
            "profit_factor": self.profit_factor,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class LaboratoryReport:
    generated_at: datetime
    observation_count: int
    folds: tuple[WalkForwardFold, ...]
    passed_folds: int
    status: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.astimezone(UTC).isoformat(),
            "observation_count": self.observation_count,
            "folds": [fold.to_dict() for fold in self.folds],
            "passed_folds": self.passed_folds,
            "status": self.status,
            "reasons": list(self.reasons),
        }
