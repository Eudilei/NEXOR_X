from datetime import UTC, datetime, timedelta

from nexor_x.laboratory import CalibrationEngine, OutcomeObservation


def obs(index: int, realized_r: float, edge: float = 0.5) -> OutcomeObservation:
    return OutcomeObservation(
        symbol="BTCUSDT",
        decision="LONG_BIAS",
        raw_edge=edge,
        regime="TREND_UP",
        realized_r=realized_r,
        closed_at=datetime(2025, 1, 1, tzinfo=UTC) + timedelta(minutes=index),
    )


def test_calibration_refuses_small_samples() -> None:
    estimate = CalibrationEngine(minimum_samples=10).estimate(
        0.5, [obs(i, 1.0) for i in range(9)], decision="LONG_BIAS", regime="TREND_UP"
    )
    assert estimate.ready is False
    assert estimate.sample_count == 9


def test_calibration_computes_expected_r_and_pf() -> None:
    data = [obs(i, 1.0 if i < 20 else -0.5) for i in range(30)]
    estimate = CalibrationEngine(minimum_samples=30).estimate(
        0.5, data, decision="LONG_BIAS", regime="TREND_UP"
    )
    assert estimate.ready is True
    assert estimate.expected_r == 0.5
    assert estimate.profit_factor == 4.0
    assert 0.6 < estimate.win_probability < 0.7


def test_calibration_is_context_specific() -> None:
    data = [obs(i, 1.0) for i in range(30)]
    estimate = CalibrationEngine(minimum_samples=30).estimate(
        0.5, data, decision="SHORT_BIAS", regime="TREND_UP"
    )
    assert estimate.ready is False
    assert estimate.sample_count == 0
