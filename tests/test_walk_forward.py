from datetime import UTC, datetime, timedelta

from nexor_x.laboratory import CalibrationEngine, OutcomeObservation, WalkForwardValidator


def make_data(count: int, positive: bool = True) -> list[OutcomeObservation]:
    return [
        OutcomeObservation(
            symbol="BTCUSDT",
            decision="LONG_BIAS",
            raw_edge=0.5,
            regime="TREND_UP",
            realized_r=1.0 if positive or i % 4 else -0.5,
            closed_at=datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=i),
        )
        for i in range(count)
    ]


def test_walk_forward_rejects_insufficient_data() -> None:
    report = WalkForwardValidator(CalibrationEngine(minimum_samples=10)).run(make_data(15))
    assert report.status == "INSUFFICIENT_DATA"


def test_walk_forward_uses_only_prior_training_data() -> None:
    report = WalkForwardValidator(CalibrationEngine(minimum_samples=10), folds=3).run(
        make_data(80)
    )
    assert report.status in {"APPROVED", "REJECTED"}
    assert len(report.folds) == 3
    assert all(fold.train_count < 80 for fold in report.folds)
