from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable

from .models import (
    StrategyDefinition,
    StrategyMetric,
    StrategyRanking,
    StrategySelection,
    StrategyStatus,
)


@dataclass(frozen=True, slots=True)
class OrchestratorPolicy:
    minimum_samples: int = 60
    minimum_profit_factor: float = 1.10
    minimum_expected_r: float = 0.05
    minimum_walk_forward_pass_ratio: float = 0.60
    maximum_ruin_probability: float = 0.05
    maximum_brier_score: float = 0.25
    switch_hysteresis: float = 0.08

    def __post_init__(self) -> None:
        if self.minimum_samples < 1:
            raise ValueError("minimum_samples must be positive")
        if self.minimum_profit_factor < 0:
            raise ValueError("minimum_profit_factor cannot be negative")
        if not 0 <= self.minimum_walk_forward_pass_ratio <= 1:
            raise ValueError("minimum_walk_forward_pass_ratio must be between 0 and 1")
        if not 0 <= self.maximum_ruin_probability <= 1:
            raise ValueError("maximum_ruin_probability must be between 0 and 1")
        if not 0 <= self.maximum_brier_score <= 1:
            raise ValueError("maximum_brier_score must be between 0 and 1")
        if self.switch_hysteresis < 0:
            raise ValueError("switch_hysteresis cannot be negative")


class MetaStrategyOrchestrator:
    """Ranks validated strategy candidates without authorizing execution.

    The orchestrator is deliberately deterministic and explainable. It does not
    create signals, estimate probabilities, or place orders. It only compares
    already-computed strategy metrics for the current context.
    """

    def __init__(
        self,
        definitions: Iterable[StrategyDefinition],
        policy: OrchestratorPolicy | None = None,
    ) -> None:
        self._definitions = {item.strategy_id: item for item in definitions}
        self.policy = policy or OrchestratorPolicy()

    @property
    def definitions(self) -> tuple[StrategyDefinition, ...]:
        return tuple(self._definitions.values())

    def rank(
        self,
        *,
        symbol: str,
        regime: str,
        decision: str,
        metrics: Iterable[StrategyMetric],
        current_strategy_id: str | None = None,
    ) -> StrategySelection:
        normalized_symbol = symbol.strip().upper()
        normalized_regime = regime.strip().upper()
        normalized_decision = decision.strip().upper()

        rankings: list[StrategyRanking] = []
        for metric in metrics:
            definition = self._definitions.get(metric.strategy_id)
            if definition is None:
                continue
            if definition.status not in {StrategyStatus.RESEARCH, StrategyStatus.PAPER}:
                continue
            if not definition.supports(normalized_regime, normalized_decision):
                continue
            if metric.regime.upper() != normalized_regime:
                continue
            if metric.decision.upper() != normalized_decision:
                continue
            rankings.append(self._evaluate(metric))

        rankings.sort(key=lambda item: (item.eligible, item.score), reverse=True)
        eligible = [item for item in rankings if item.eligible]

        if not eligible:
            return StrategySelection(
                symbol=normalized_symbol,
                regime=normalized_regime,
                decision=normalized_decision,
                selected_strategy_id=None,
                rankings=tuple(rankings),
                status="NO_ELIGIBLE_STRATEGY",
                explanation="Nenhuma estrategia passou por todos os criterios quantitativos.",
            )

        best = eligible[0]
        selected = best

        if current_strategy_id:
            current = next(
                (item for item in eligible if item.strategy_id == current_strategy_id),
                None,
            )
            if current is not None and best.score - current.score < self.policy.switch_hysteresis:
                selected = current

        explanation = (
            f"{selected.strategy_id} liderou o contexto {normalized_regime}/"
            f"{normalized_decision} com score comparativo {selected.score:.4f}. "
            "A selecao permanece observacional e nao autoriza ordens."
        )
        return StrategySelection(
            symbol=normalized_symbol,
            regime=normalized_regime,
            decision=normalized_decision,
            selected_strategy_id=selected.strategy_id,
            rankings=tuple(rankings),
            status="SELECTED_FOR_RESEARCH",
            explanation=explanation,
        )

    def _evaluate(self, metric: StrategyMetric) -> StrategyRanking:
        reasons: list[str] = []
        p = self.policy

        if metric.sample_count < p.minimum_samples:
            reasons.append("INSUFFICIENT_SAMPLES")
        if metric.profit_factor < p.minimum_profit_factor:
            reasons.append("PROFIT_FACTOR_BELOW_MINIMUM")
        if metric.expected_r < p.minimum_expected_r:
            reasons.append("EXPECTED_R_BELOW_MINIMUM")
        if (
            metric.walk_forward_pass_ratio is None
            or metric.walk_forward_pass_ratio < p.minimum_walk_forward_pass_ratio
        ):
            reasons.append("WALK_FORWARD_NOT_APPROVED")
        if (
            metric.monte_carlo_ruin_probability is None
            or metric.monte_carlo_ruin_probability > p.maximum_ruin_probability
        ):
            reasons.append("MONTE_CARLO_RISK_TOO_HIGH")
        if metric.brier_score is None or metric.brier_score > p.maximum_brier_score:
            reasons.append("CALIBRATION_NOT_APPROVED")

        values = (
            metric.profit_factor,
            metric.expected_r,
            metric.win_rate,
            metric.max_drawdown_r,
        )
        if not all(isfinite(value) for value in values):
            reasons.append("NON_FINITE_METRIC")

        score = self._score(metric)
        return StrategyRanking(
            strategy_id=metric.strategy_id,
            score=score,
            eligible=not reasons,
            reasons=tuple(reasons),
            metric=metric,
        )

    @staticmethod
    def _score(metric: StrategyMetric) -> float:
        walk_forward = metric.walk_forward_pass_ratio or 0.0
        ruin_safety = 1.0 - (metric.monte_carlo_ruin_probability or 1.0)
        calibration = 1.0 - min(max(metric.brier_score or 1.0, 0.0), 1.0)
        drawdown_penalty = max(metric.max_drawdown_r, 0.0)

        return round(
            0.24 * min(metric.profit_factor / 2.0, 1.5)
            + 0.24 * min(max(metric.expected_r, -1.0), 1.0)
            + 0.12 * min(max(metric.win_rate, 0.0), 1.0)
            + 0.16 * walk_forward
            + 0.12 * ruin_safety
            + 0.12 * calibration
            - 0.05 * drawdown_penalty,
            6,
        )
