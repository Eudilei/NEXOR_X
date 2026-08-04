from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import isfinite
from typing import Iterable

from .models import AllocationCandidate, AllocationPlan, AllocationResult


@dataclass(frozen=True, slots=True)
class AllocationPolicy:
    maximum_candidates: int = 5
    maximum_weight_per_candidate: float = 0.35
    maximum_weight_per_correlation_group: float = 0.55
    minimum_score: float = 0.20
    minimum_expected_r: float = 0.05
    minimum_profit_factor: float = 1.10
    minimum_walk_forward_pass_ratio: float = 0.60
    maximum_ruin_probability: float = 0.05
    maximum_candidate_drawdown_r: float = 8.0
    maximum_portfolio_risk_pct: float = 10.0
    recovery_drawdown_trigger_pct: float = 10.0
    hard_stop_drawdown_pct: float = 25.0
    recovery_risk_multiplier: float = 0.35

    def __post_init__(self) -> None:
        if self.maximum_candidates < 1:
            raise ValueError("maximum_candidates must be positive")
        for value, name in (
            (self.maximum_weight_per_candidate, "maximum_weight_per_candidate"),
            (self.maximum_weight_per_correlation_group, "maximum_weight_per_correlation_group"),
        ):
            if not 0 < value <= 1:
                raise ValueError(f"{name} must be in (0, 1]")
        if self.maximum_portfolio_risk_pct <= 0:
            raise ValueError("maximum_portfolio_risk_pct must be positive")
        if not 0 < self.recovery_risk_multiplier <= 1:
            raise ValueError("recovery_risk_multiplier must be in (0, 1]")


class AdaptivePortfolioAllocator:
    """Creates an explainable research allocation plan.

    It never changes account equity, positions, or exchange orders.
    """

    def __init__(self, policy: AllocationPolicy | None = None) -> None:
        self.policy = policy or AllocationPolicy()

    def allocate(
        self,
        candidates: Iterable[AllocationCandidate],
        *,
        portfolio_drawdown_pct: float,
    ) -> AllocationPlan:
        if portfolio_drawdown_pct >= self.policy.hard_stop_drawdown_pct:
            return AllocationPlan(
                status="HARD_STOP",
                allocations=(),
                total_weight=0.0,
                total_risk_budget_pct=0.0,
                unallocated_weight=1.0,
                explanation="Drawdown atingiu o hard stop; nenhuma alocacao e permitida.",
            )

        evaluated = [self._evaluate(candidate) for candidate in candidates]
        eligible_pairs = [
            (candidate, reasons)
            for candidate, reasons in evaluated
            if not reasons
        ]
        eligible_pairs.sort(key=lambda item: self._quality(item[0]), reverse=True)
        eligible_pairs = eligible_pairs[: self.policy.maximum_candidates]

        if not eligible_pairs:
            rejected = tuple(
                AllocationResult(
                    strategy_id=candidate.strategy_id,
                    symbol=candidate.symbol,
                    direction=candidate.direction,
                    target_weight=0.0,
                    risk_budget_pct=0.0,
                    eligible=False,
                    reasons=tuple(reasons),
                )
                for candidate, reasons in evaluated
            )
            return AllocationPlan(
                status="NO_ELIGIBLE_CANDIDATES",
                allocations=rejected,
                total_weight=0.0,
                total_risk_budget_pct=0.0,
                unallocated_weight=1.0,
                explanation="Nenhum candidato passou pelos criterios de robustez.",
            )

        qualities = [max(self._quality(candidate), 0.000001) for candidate, _ in eligible_pairs]
        total_quality = sum(qualities)
        preliminary = [quality / total_quality for quality in qualities]

        group_used: dict[str, float] = defaultdict(float)
        weights: list[float] = []
        for (candidate, _), weight in zip(eligible_pairs, preliminary, strict=True):
            weight = min(weight, self.policy.maximum_weight_per_candidate)
            available_group = max(
                self.policy.maximum_weight_per_correlation_group
                - group_used[candidate.correlation_group],
                0.0,
            )
            weight = min(weight, available_group)
            group_used[candidate.correlation_group] += weight
            weights.append(weight)

        total_weight = sum(weights)
        if total_weight > 1.0:
            weights = [weight / total_weight for weight in weights]
            total_weight = 1.0

        risk_multiplier = (
            self.policy.recovery_risk_multiplier
            if portfolio_drawdown_pct >= self.policy.recovery_drawdown_trigger_pct
            else 1.0
        )
        total_risk_budget = self.policy.maximum_portfolio_risk_pct * risk_multiplier

        allocations = tuple(
            AllocationResult(
                strategy_id=candidate.strategy_id,
                symbol=candidate.symbol,
                direction=candidate.direction,
                target_weight=round(weight, 8),
                risk_budget_pct=round(total_risk_budget * weight, 8),
                eligible=True,
                reasons=(),
            )
            for (candidate, _), weight in zip(eligible_pairs, weights, strict=True)
            if weight > 0
        )

        status = (
            "RECOVERY_ALLOCATION"
            if risk_multiplier < 1.0
            else "RESEARCH_ALLOCATION_READY"
        )
        return AllocationPlan(
            status=status,
            allocations=allocations,
            total_weight=round(sum(item.target_weight for item in allocations), 8),
            total_risk_budget_pct=round(
                sum(item.risk_budget_pct for item in allocations), 8
            ),
            unallocated_weight=round(
                max(1.0 - sum(item.target_weight for item in allocations), 0.0), 8
            ),
            explanation=(
                "Plano observacional criado com limites por candidato, grupo de "
                "correlacao e drawdown. Nao autoriza ordens."
            ),
        )

    def _evaluate(self, candidate: AllocationCandidate) -> tuple[AllocationCandidate, list[str]]:
        p = self.policy
        reasons: list[str] = []
        values = (
            candidate.score,
            candidate.expected_r,
            candidate.profit_factor,
            candidate.walk_forward_pass_ratio,
            candidate.monte_carlo_ruin_probability,
            candidate.max_drawdown_r,
            candidate.current_drawdown_pct,
        )
        if not all(isfinite(value) for value in values):
            reasons.append("NON_FINITE_METRIC")
        if candidate.score < p.minimum_score:
            reasons.append("SCORE_BELOW_MINIMUM")
        if candidate.expected_r < p.minimum_expected_r:
            reasons.append("EXPECTED_R_BELOW_MINIMUM")
        if candidate.profit_factor < p.minimum_profit_factor:
            reasons.append("PROFIT_FACTOR_BELOW_MINIMUM")
        if candidate.walk_forward_pass_ratio < p.minimum_walk_forward_pass_ratio:
            reasons.append("WALK_FORWARD_NOT_APPROVED")
        if candidate.monte_carlo_ruin_probability > p.maximum_ruin_probability:
            reasons.append("MONTE_CARLO_RISK_TOO_HIGH")
        if candidate.max_drawdown_r > p.maximum_candidate_drawdown_r:
            reasons.append("CANDIDATE_DRAWDOWN_TOO_HIGH")
        return candidate, reasons

    @staticmethod
    def _quality(candidate: AllocationCandidate) -> float:
        safety = 1.0 - min(max(candidate.monte_carlo_ruin_probability, 0.0), 1.0)
        drawdown_penalty = 1.0 / (1.0 + max(candidate.max_drawdown_r, 0.0))
        return (
            0.30 * candidate.score
            + 0.25 * candidate.expected_r
            + 0.15 * min(candidate.profit_factor / 2.0, 1.5)
            + 0.15 * candidate.walk_forward_pass_ratio
            + 0.10 * safety
            + 0.05 * drawdown_penalty
        )
