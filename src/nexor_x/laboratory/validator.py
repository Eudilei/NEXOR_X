from __future__ import annotations

from datetime import UTC, datetime

from .calibration import CalibrationEngine
from .models import LaboratoryReport, OutcomeObservation, WalkForwardFold


class WalkForwardValidator:
    def __init__(self, calibration: CalibrationEngine, folds: int = 5) -> None:
        if folds < 2:
            raise ValueError("folds must be at least 2")
        self.calibration = calibration
        self.folds = folds

    def run(self, observations: list[OutcomeObservation]) -> LaboratoryReport:
        ordered = sorted(observations, key=lambda item: item.closed_at)
        if len(ordered) < max(self.calibration.minimum_samples * 2, self.folds * 10):
            return LaboratoryReport(
                generated_at=datetime.now(UTC),
                observation_count=len(ordered),
                folds=(),
                passed_folds=0,
                status="INSUFFICIENT_DATA",
                reasons=("dados insuficientes para walk-forward causal",),
            )

        fold_size = max(1, len(ordered) // (self.folds + 1))
        results: list[WalkForwardFold] = []
        for index in range(self.folds):
            train_end = fold_size * (index + 1)
            test_end = min(train_end + fold_size, len(ordered))
            train = ordered[:train_end]
            test = ordered[train_end:test_end]
            if not test:
                break

            expected_values: list[float] = []
            accepted: list[OutcomeObservation] = []
            for item in test:
                estimate = self.calibration.estimate(
                    item.raw_edge,
                    train,
                    decision=item.decision,
                    regime=item.regime,
                )
                if estimate.ready and estimate.expected_r is not None and estimate.expected_r > 0:
                    expected_values.append(estimate.expected_r)
                    accepted.append(item)

            realized_r = sum(item.realized_r for item in accepted)
            gross_profit = sum(item.realized_r for item in accepted if item.realized_r > 0)
            gross_loss = abs(sum(item.realized_r for item in accepted if item.realized_r < 0))
            pf = gross_profit / gross_loss if gross_loss > 0 else (None if not accepted else float("inf"))
            expected_r = sum(expected_values) / len(expected_values) if expected_values else None
            passed = bool(accepted) and realized_r > 0 and (pf is None or pf > 1.0)
            results.append(
                WalkForwardFold(
                    fold=index + 1,
                    train_count=len(train),
                    test_count=len(accepted),
                    expected_r=round(expected_r, 6) if expected_r is not None else None,
                    realized_r=round(realized_r, 6),
                    profit_factor=(round(pf, 6) if pf not in (None, float("inf")) else pf),
                    passed=passed,
                )
            )

        passed_folds = sum(1 for item in results if item.passed)
        required = max(2, (len(results) * 3 + 4) // 5)
        status = "APPROVED" if results and passed_folds >= required else "REJECTED"
        reasons = (
            f"{passed_folds}/{len(results)} folds positivos",
            "aprovacao nao libera LIVE; certificacao operacional continua obrigatoria",
        )
        return LaboratoryReport(
            generated_at=datetime.now(UTC),
            observation_count=len(ordered),
            folds=tuple(results),
            passed_folds=passed_folds,
            status=status,
            reasons=reasons,
        )
