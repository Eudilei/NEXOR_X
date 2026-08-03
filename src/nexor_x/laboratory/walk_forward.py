from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable

from nexor_x.infrastructure.database import DatabaseService

from .calibration import CalibrationEngine
from .models import OutcomeObservation


@dataclass(frozen=True, slots=True)
class WalkForwardConfig:
    folds: int = 5
    minimum_train_observations: int = 60
    minimum_test_observations: int = 20
    minimum_pass_ratio: float = 0.60
    minimum_profit_factor: float = 1.05
    minimum_expected_r: float = 0.0

    def validate(self) -> None:
        if not 2 <= self.folds <= 20:
            raise ValueError("folds must be between 2 and 20")
        if self.minimum_train_observations < 20:
            raise ValueError("minimum_train_observations must be at least 20")
        if self.minimum_test_observations < 5:
            raise ValueError("minimum_test_observations must be at least 5")
        if not 0 < self.minimum_pass_ratio <= 1:
            raise ValueError("minimum_pass_ratio must be in (0, 1]")
        if self.minimum_profit_factor < 0:
            raise ValueError("minimum_profit_factor must be non-negative")


@dataclass(frozen=True, slots=True)
class WalkForwardRun:
    run_id: str
    generated_at: datetime
    status: str
    observation_count: int
    eligible_observations: int
    folds_requested: int
    folds_completed: int
    passed_folds: int
    pass_ratio: float
    aggregate_realized_r: float
    aggregate_profit_factor: float | None
    worst_fold_realized_r: float | None
    reason: str
    folds: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "generated_at": self.generated_at.astimezone(UTC).isoformat(),
            "status": self.status,
            "observation_count": self.observation_count,
            "eligible_observations": self.eligible_observations,
            "folds_requested": self.folds_requested,
            "folds_completed": self.folds_completed,
            "passed_folds": self.passed_folds,
            "pass_ratio": self.pass_ratio,
            "aggregate_realized_r": self.aggregate_realized_r,
            "aggregate_profit_factor": self.aggregate_profit_factor,
            "worst_fold_realized_r": self.worst_fold_realized_r,
            "reason": self.reason,
            "folds": list(self.folds),
            "execution_allowed": False,
            "live_certified": False,
        }


class ContinuousWalkForwardEngine:
    """Expanding-window walk-forward using only prior observations per fold."""

    def __init__(self, database: DatabaseService, calibration: CalibrationEngine) -> None:
        self.database = database
        self.calibration = calibration

    async def run(
        self,
        observations: Iterable[OutcomeObservation],
        config: WalkForwardConfig,
        *,
        symbol: str | None = None,
        decision: str | None = None,
        regime: str | None = None,
    ) -> WalkForwardRun:
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
        minimum_total = config.minimum_train_observations + config.minimum_test_observations
        if len(ordered) < minimum_total:
            report = WalkForwardRun(
                run_id, generated_at, "INSUFFICIENT_DATA", len(ordered), 0,
                config.folds, 0, 0, 0.0, 0.0, None, None,
                f"dados insuficientes: {len(ordered)}/{minimum_total}", (),
            )
            await self._persist(report, symbol, decision, regime)
            return report

        available_test = len(ordered) - config.minimum_train_observations
        fold_size = max(config.minimum_test_observations, available_test // config.folds)
        folds: list[dict[str, object]] = []
        eligible_total = 0
        all_realized: list[float] = []
        for index in range(config.folds):
            train_end = config.minimum_train_observations + index * fold_size
            if train_end >= len(ordered):
                break
            test_end = len(ordered) if index == config.folds - 1 else min(len(ordered), train_end + fold_size)
            test = ordered[train_end:test_end]
            if len(test) < config.minimum_test_observations:
                break
            train = ordered[:train_end]
            accepted: list[OutcomeObservation] = []
            predicted: list[float] = []
            for item in test:
                estimate = self.calibration.estimate(
                    item.raw_edge, train, decision=item.decision, regime=item.regime
                )
                if estimate.ready and estimate.expected_r is not None and estimate.expected_r > config.minimum_expected_r:
                    accepted.append(item)
                    predicted.append(estimate.expected_r)
            realized = [item.realized_r for item in accepted]
            eligible_total += len(accepted)
            all_realized.extend(realized)
            gross_profit = sum(x for x in realized if x > 0)
            gross_loss = abs(sum(x for x in realized if x < 0))
            pf = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if realized and gross_profit > 0 else None)
            realized_r = sum(realized)
            expected_r = sum(predicted) / len(predicted) if predicted else None
            passed = bool(realized) and realized_r > 0 and pf is not None and pf >= config.minimum_profit_factor
            folds.append({
                "fold": index + 1,
                "train_count": len(train),
                "test_window_count": len(test),
                "eligible_count": len(accepted),
                "train_end": train[-1].closed_at.astimezone(UTC).isoformat(),
                "test_start": test[0].closed_at.astimezone(UTC).isoformat(),
                "test_end": test[-1].closed_at.astimezone(UTC).isoformat(),
                "expected_r": round(expected_r, 6) if expected_r is not None else None,
                "realized_r": round(realized_r, 6),
                "profit_factor": None if pf is None else ("inf" if pf == float("inf") else round(pf, 6)),
                "passed": passed,
            })

        passed = sum(1 for fold in folds if fold["passed"])
        ratio = passed / len(folds) if folds else 0.0
        gross_profit = sum(x for x in all_realized if x > 0)
        gross_loss = abs(sum(x for x in all_realized if x < 0))
        aggregate_pf = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if all_realized and gross_profit > 0 else None)
        aggregate_r = sum(all_realized)
        worst = min((float(fold["realized_r"]) for fold in folds), default=None)
        status = "APPROVED" if folds and ratio >= config.minimum_pass_ratio and aggregate_r > 0 and aggregate_pf is not None and aggregate_pf >= config.minimum_profit_factor else "REJECTED"
        reason = f"{passed}/{len(folds)} folds aprovados; uso operacional continua bloqueado"
        report = WalkForwardRun(
            run_id, generated_at, status, len(ordered), eligible_total,
            config.folds, len(folds), passed, round(ratio, 6), round(aggregate_r, 6),
            None if aggregate_pf is None else (float("inf") if aggregate_pf == float("inf") else round(aggregate_pf, 6)),
            round(worst, 6) if worst is not None else None, reason, tuple(folds),
        )
        await self._persist(report, symbol, decision, regime)
        return report

    async def _persist(self, report: WalkForwardRun, symbol: str | None, decision: str | None, regime: str | None) -> None:
        import json
        await self.database.execute(
            """INSERT INTO walk_forward_runs
            (run_id, generated_at, status, observation_count, eligible_observations,
             folds_requested, folds_completed, passed_folds, pass_ratio,
             aggregate_realized_r, aggregate_profit_factor, worst_fold_realized_r,
             reason, symbol, decision, regime, folds_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report.run_id, report.generated_at.isoformat(), report.status,
                report.observation_count, report.eligible_observations,
                report.folds_requested, report.folds_completed, report.passed_folds,
                report.pass_ratio, report.aggregate_realized_r,
                report.aggregate_profit_factor, report.worst_fold_realized_r,
                report.reason, symbol, decision, regime,
                json.dumps(list(report.folds), ensure_ascii=False),
            ),
        )

    async def latest(self) -> dict[str, object]:
        import json
        rows = await self.database.fetchall(
            """SELECT run_id, generated_at, status, observation_count, eligible_observations,
            folds_requested, folds_completed, passed_folds, pass_ratio,
            aggregate_realized_r, aggregate_profit_factor, worst_fold_realized_r,
            reason, symbol, decision, regime, folds_json
            FROM walk_forward_runs ORDER BY generated_at DESC LIMIT 1"""
        )
        if not rows:
            return {"status": "NOT_RUN", "execution_allowed": False, "live_certified": False}
        row = rows[0]
        return {
            "run_id": row[0], "generated_at": row[1], "status": row[2],
            "observation_count": row[3], "eligible_observations": row[4],
            "folds_requested": row[5], "folds_completed": row[6],
            "passed_folds": row[7], "pass_ratio": row[8],
            "aggregate_realized_r": row[9], "aggregate_profit_factor": row[10],
            "worst_fold_realized_r": row[11], "reason": row[12],
            "symbol": row[13], "decision": row[14], "regime": row[15],
            "folds": json.loads(str(row[16])),
            "execution_allowed": False, "live_certified": False,
        }
