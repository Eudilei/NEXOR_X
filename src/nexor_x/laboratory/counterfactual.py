from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable

from nexor_x.infrastructure.database import DatabaseService

from .models import OutcomeObservation


@dataclass(frozen=True, slots=True)
class CounterfactualConfig:
    minimum_observations: int = 60
    minimum_kept_observations: int = 20
    edge_thresholds: tuple[float, ...] = (0.10, 0.20, 0.30, 0.40, 0.50)

    def validate(self) -> None:
        if self.minimum_observations < 20:
            raise ValueError("minimum_observations must be at least 20")
        if self.minimum_kept_observations < 5:
            raise ValueError("minimum_kept_observations must be at least 5")
        if not self.edge_thresholds:
            raise ValueError("edge_thresholds cannot be empty")
        if any(not 0 <= value <= 1 for value in self.edge_thresholds):
            raise ValueError("edge thresholds must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class CounterfactualRun:
    run_id: str
    generated_at: datetime
    status: str
    observation_count: int
    scenario_count: int
    best_scenario: str | None
    baseline_realized_r: float
    baseline_profit_factor: float | None
    best_net_benefit_r: float | None
    reason: str
    scenarios: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "generated_at": self.generated_at.astimezone(UTC).isoformat(),
            "status": self.status,
            "observation_count": self.observation_count,
            "scenario_count": self.scenario_count,
            "best_scenario": self.best_scenario,
            "baseline_realized_r": self.baseline_realized_r,
            "baseline_profit_factor": self.baseline_profit_factor,
            "best_net_benefit_r": self.best_net_benefit_r,
            "reason": self.reason,
            "scenarios": list(self.scenarios),
            "causal_claim": False,
            "execution_allowed": False,
            "live_certified": False,
        }


class CounterfactualEngine:
    """Historical policy comparison, not a causal market simulator.

    It asks how recorded outcomes would have changed if a deterministic admission
    policy had kept or blocked the same historical observations. It never invents
    fills, prices, or unobserved outcomes and therefore must not be interpreted as
    proof that a policy will cause the same result in future data.
    """

    def __init__(self, database: DatabaseService) -> None:
        self.database = database

    async def run(
        self,
        observations: Iterable[OutcomeObservation],
        config: CounterfactualConfig,
        *,
        symbol: str | None = None,
        decision: str | None = None,
        regime: str | None = None,
    ) -> CounterfactualRun:
        config.validate()
        ordered = sorted(
            (
                item for item in observations
                if (symbol is None or item.symbol == symbol)
                and (decision is None or item.decision == decision)
                and (regime is None or item.regime == regime)
            ),
            key=lambda item: item.closed_at,
        )
        run_id = str(uuid.uuid4())
        generated_at = datetime.now(UTC)
        baseline_r = sum(item.realized_r for item in ordered)
        baseline_pf = self._profit_factor(item.realized_r for item in ordered)
        if len(ordered) < config.minimum_observations:
            report = CounterfactualRun(
                run_id, generated_at, "INSUFFICIENT_DATA", len(ordered), 0, None,
                round(baseline_r, 6), baseline_pf, None,
                f"dados insuficientes: {len(ordered)}/{config.minimum_observations}", (),
            )
            await self._persist(report, symbol, decision, regime)
            return report

        scenarios: list[dict[str, object]] = []
        for threshold in sorted(set(config.edge_thresholds)):
            scenarios.append(self._evaluate_threshold(ordered, threshold, config))

        for direction_name in ("LONG_BIAS", "SHORT_BIAS"):
            scenarios.append(self._evaluate_policy(
                ordered,
                name=f"ONLY_{direction_name}",
                predicate=lambda item, d=direction_name: item.decision == d,
                minimum_kept=config.minimum_kept_observations,
            ))

        regimes = sorted({item.regime for item in ordered})
        for regime_name in regimes:
            scenarios.append(self._evaluate_policy(
                ordered,
                name=f"ONLY_REGIME_{regime_name}",
                predicate=lambda item, r=regime_name: item.regime == r,
                minimum_kept=config.minimum_kept_observations,
            ))

        eligible = [scenario for scenario in scenarios if scenario["eligible"]]
        eligible.sort(
            key=lambda item: (
                float(item["net_benefit_r"]),
                float(item["kept_expected_r"]),
                int(item["kept_count"]),
            ),
            reverse=True,
        )
        best = eligible[0] if eligible else None
        status = "IMPROVEMENT_FOUND" if best and float(best["net_benefit_r"]) > 0 else "NO_IMPROVEMENT"
        reason = (
            f"melhor politica historica: {best['name']}; beneficio liquido "
            f"{best['net_benefit_r']}R; sem alegacao causal"
            if best else "nenhuma politica manteve amostra minima"
        )
        report = CounterfactualRun(
            run_id, generated_at, status, len(ordered), len(scenarios),
            str(best["name"]) if best else None, round(baseline_r, 6), baseline_pf,
            float(best["net_benefit_r"]) if best else None, reason, tuple(scenarios),
        )
        await self._persist(report, symbol, decision, regime)
        return report

    def _evaluate_threshold(
        self, observations: list[OutcomeObservation], threshold: float,
        config: CounterfactualConfig,
    ) -> dict[str, object]:
        return self._evaluate_policy(
            observations,
            name=f"ABS_EDGE_GTE_{threshold:.2f}",
            predicate=lambda item: abs(item.raw_edge) >= threshold,
            minimum_kept=config.minimum_kept_observations,
        )

    def _evaluate_policy(self, observations, *, name, predicate, minimum_kept):
        kept = [item for item in observations if predicate(item)]
        blocked = [item for item in observations if not predicate(item)]
        kept_r = sum(item.realized_r for item in kept)
        blocked_r = sum(item.realized_r for item in blocked)
        blocked_losses = abs(sum(item.realized_r for item in blocked if item.realized_r < 0))
        blocked_winners = sum(item.realized_r for item in blocked if item.realized_r > 0)
        net_benefit = -blocked_r
        return {
            "name": name,
            "eligible": len(kept) >= minimum_kept,
            "kept_count": len(kept),
            "blocked_count": len(blocked),
            "coverage": round(len(kept) / len(observations), 6),
            "kept_realized_r": round(kept_r, 6),
            "kept_expected_r": round(kept_r / len(kept), 6) if kept else 0.0,
            "kept_profit_factor": self._profit_factor(item.realized_r for item in kept),
            "avoided_loss_r": round(blocked_losses, 6),
            "missed_profit_r": round(blocked_winners, 6),
            "blocked_net_r": round(blocked_r, 6),
            "net_benefit_r": round(net_benefit, 6),
        }

    @staticmethod
    def _profit_factor(values) -> float | None:
        values = list(values)
        gross_profit = sum(value for value in values if value > 0)
        gross_loss = abs(sum(value for value in values if value < 0))
        if gross_loss > 0:
            return round(gross_profit / gross_loss, 6)
        if values and gross_profit > 0:
            return float("inf")
        return None

    async def _persist(
        self, report: CounterfactualRun, symbol: str | None,
        decision: str | None, regime: str | None,
    ) -> None:
        await self.database.execute(
            """INSERT INTO counterfactual_runs
            (run_id, generated_at, status, observation_count, scenario_count,
             best_scenario, baseline_realized_r, baseline_profit_factor,
             best_net_benefit_r, reason, symbol, decision, regime, scenarios_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report.run_id, report.generated_at.isoformat(), report.status,
                report.observation_count, report.scenario_count, report.best_scenario,
                report.baseline_realized_r, report.baseline_profit_factor,
                report.best_net_benefit_r, report.reason, symbol, decision, regime,
                json.dumps(list(report.scenarios), ensure_ascii=False),
            ),
        )

    async def latest(self) -> dict[str, object]:
        rows = await self.database.fetchall(
            """SELECT run_id, generated_at, status, observation_count, scenario_count,
            best_scenario, baseline_realized_r, baseline_profit_factor,
            best_net_benefit_r, reason, symbol, decision, regime, scenarios_json
            FROM counterfactual_runs ORDER BY generated_at DESC LIMIT 1"""
        )
        if not rows:
            return {
                "status": "NOT_RUN", "causal_claim": False,
                "execution_allowed": False, "live_certified": False,
            }
        row = rows[0]
        return {
            "run_id": row[0], "generated_at": row[1], "status": row[2],
            "observation_count": row[3], "scenario_count": row[4],
            "best_scenario": row[5], "baseline_realized_r": row[6],
            "baseline_profit_factor": row[7], "best_net_benefit_r": row[8],
            "reason": row[9], "symbol": row[10], "decision": row[11],
            "regime": row[12], "scenarios": json.loads(str(row[13])),
            "causal_claim": False, "execution_allowed": False,
            "live_certified": False,
        }
