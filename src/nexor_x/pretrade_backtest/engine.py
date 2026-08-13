from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class ContextBacktestPolicy:
    minimum_samples: int = 30
    maximum_samples: int = 300
    minimum_profit_factor: float = 1.10
    minimum_expected_r: float = 0.05
    minimum_recent_profit_factor: float = 1.00
    minimum_recent_expected_r: float = 0.00
    maximum_drawdown_r: float = 8.0
    minimum_walk_forward_pass_ratio: float = 0.60
    folds: int = 3

    def __post_init__(self) -> None:
        if self.minimum_samples < 1:
            raise ValueError("minimum_samples must be positive")
        if self.maximum_samples < self.minimum_samples:
            raise ValueError("maximum_samples must be >= minimum_samples")
        if self.folds < 2:
            raise ValueError("folds must be >= 2")


@dataclass(frozen=True, slots=True)
class ContextBacktestReport:
    status: str
    approved: bool
    symbol: str
    decision: str
    regime: str
    sample_count: int
    profit_factor: float
    expected_r: float
    win_rate: float
    maximum_drawdown_r: float
    recent_profit_factor: float
    recent_expected_r: float
    walk_forward_pass_ratio: float
    checks: dict[str, bool]
    blockers: tuple[str, ...]
    execution_allowed: bool = False
    live_execution_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        return data


class ContextBacktestEngine:
    """Fast historical validation for the exact current market context.

    The engine consumes already-closed historical outcomes. It does not train on
    the current trade and never fabricates missing evidence.
    """

    def __init__(self, policy: ContextBacktestPolicy | None = None) -> None:
        self.policy = policy or ContextBacktestPolicy()

    def evaluate(
        self,
        *,
        symbol: str,
        decision: str,
        regime: str,
        realized_r: Iterable[float],
    ) -> ContextBacktestReport:
        values = [float(value) for value in realized_r]
        values = [value for value in values if isfinite(value)]
        values = values[-self.policy.maximum_samples :]

        sample_count = len(values)
        pf = self._profit_factor(values)
        expected_r = self._mean(values)
        win_rate = (
            sum(1 for value in values if value > 0) / sample_count
            if sample_count
            else 0.0
        )
        maximum_drawdown_r = self._maximum_drawdown(values)

        recent_count = max(min(sample_count // 3, 100), 1) if values else 0
        recent = values[-recent_count:] if recent_count else []
        recent_pf = self._profit_factor(recent)
        recent_expected_r = self._mean(recent)
        walk_forward_pass_ratio = self._walk_forward_pass_ratio(values)

        checks = {
            "MINIMUM_SAMPLES": sample_count >= self.policy.minimum_samples,
            "PROFIT_FACTOR": pf >= self.policy.minimum_profit_factor,
            "EXPECTED_R": expected_r >= self.policy.minimum_expected_r,
            "RECENT_PROFIT_FACTOR": (
                recent_pf >= self.policy.minimum_recent_profit_factor
            ),
            "RECENT_EXPECTED_R": (
                recent_expected_r >= self.policy.minimum_recent_expected_r
            ),
            "MAXIMUM_DRAWDOWN": (
                maximum_drawdown_r <= self.policy.maximum_drawdown_r
            ),
            "WALK_FORWARD": (
                walk_forward_pass_ratio
                >= self.policy.minimum_walk_forward_pass_ratio
            ),
        }
        blockers = tuple(name for name, passed in checks.items() if not passed)
        approved = not blockers

        return ContextBacktestReport(
            status="APPROVED" if approved else "BLOCKED",
            approved=approved,
            symbol=symbol.upper(),
            decision=decision.upper(),
            regime=regime.upper(),
            sample_count=sample_count,
            profit_factor=round(pf, 6),
            expected_r=round(expected_r, 6),
            win_rate=round(win_rate, 6),
            maximum_drawdown_r=round(maximum_drawdown_r, 6),
            recent_profit_factor=round(recent_pf, 6),
            recent_expected_r=round(recent_expected_r, 6),
            walk_forward_pass_ratio=round(walk_forward_pass_ratio, 6),
            checks=checks,
            blockers=blockers,
            execution_allowed=False,
            live_execution_allowed=False,
        )

    @staticmethod
    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _profit_factor(values: list[float]) -> float:
        gross_profit = sum(value for value in values if value > 0)
        gross_loss = abs(sum(value for value in values if value < 0))
        if gross_loss > 0:
            return gross_profit / gross_loss
        if gross_profit > 0:
            return 999.0
        return 0.0

    @staticmethod
    def _maximum_drawdown(values: list[float]) -> float:
        equity = 0.0
        peak = 0.0
        maximum_drawdown = 0.0
        for value in values:
            equity += value
            peak = max(peak, equity)
            maximum_drawdown = max(maximum_drawdown, peak - equity)
        return maximum_drawdown

    def _walk_forward_pass_ratio(self, values: list[float]) -> float:
        if len(values) < self.policy.minimum_samples:
            return 0.0

        fold_size = max(len(values) // self.policy.folds, 1)
        folds: list[list[float]] = []
        start = 0
        for index in range(self.policy.folds):
            end = (
                len(values)
                if index == self.policy.folds - 1
                else start + fold_size
            )
            fold = values[start:end]
            if fold:
                folds.append(fold)
            start = end

        if not folds:
            return 0.0

        passed = 0
        for fold in folds:
            pf = self._profit_factor(fold)
            expected_r = self._mean(fold)
            if (
                pf >= self.policy.minimum_profit_factor
                and expected_r >= self.policy.minimum_expected_r
            ):
                passed += 1

        return passed / len(folds)
