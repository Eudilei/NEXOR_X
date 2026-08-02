from datetime import UTC, datetime, timedelta

from nexor_x.laboratory.models import OutcomeObservation
from nexor_x.laboratory.probability import ProbabilityCalibrationEngine


def observations(count: int = 120, positive_bias: bool = True):
    start = datetime(2024, 1, 1, tzinfo=UTC)
    items = []
    for i in range(count):
        edge = -0.9 + 1.8 * i / max(1, count - 1)
        threshold = 0.35 if positive_bias else 0.70
        won = ((i * 37) % 100) / 100 < max(0.05, min(0.95, threshold + edge * 0.25))
        items.append(OutcomeObservation(
            symbol="BTCUSDT", decision="LONG_BIAS", raw_edge=edge,
            regime="TREND_UP", realized_r=1.4 if won else -1.0,
            closed_at=start + timedelta(hours=i),
        ))
    return items


def test_probability_calibration_requires_minimum_sample():
    engine = ProbabilityCalibrationEngine(minimum_samples=60)
    report = engine.calibrate(0.4, observations(30), decision="LONG_BIAS", regime="TREND_UP")
    assert report.ready is False
    assert report.probability is None
    assert report.to_dict()["execution_allowed"] is False


def test_probability_calibration_returns_bounded_metrics():
    engine = ProbabilityCalibrationEngine(minimum_samples=60)
    report = engine.calibrate(0.6, observations(), decision="LONG_BIAS", regime="TREND_UP")
    assert report.ready is True
    assert report.method in {"PLATT", "ISOTONIC"}
    assert 0 < report.probability < 1
    assert 0 <= report.confidence_low_95 <= report.probability <= report.confidence_high_95 <= 1
    assert report.brier_score is not None and 0 <= report.brier_score <= 1
    assert report.expected_calibration_error is not None and 0 <= report.expected_calibration_error <= 1
    assert report.fractional_kelly is not None and 0 <= report.fractional_kelly <= 1
    assert report.to_dict()["live_certified"] is False


def test_higher_raw_edge_does_not_reduce_isotonic_probability_materially():
    engine = ProbabilityCalibrationEngine(minimum_samples=60)
    low = engine.calibrate(-0.6, observations(), decision="LONG_BIAS", regime="TREND_UP")
    high = engine.calibrate(0.6, observations(), decision="LONG_BIAS", regime="TREND_UP")
    assert high.probability is not None and low.probability is not None
    assert high.probability >= low.probability - 0.05


def test_context_is_segregated():
    engine = ProbabilityCalibrationEngine(minimum_samples=60)
    mixed = observations(120) + [
        OutcomeObservation("BTCUSDT", "SHORT_BIAS", 0.5, "TREND_DOWN", -1.0, datetime(2025, 1, 1, tzinfo=UTC) + timedelta(hours=i))
        for i in range(120)
    ]
    report = engine.calibrate(0.5, mixed, decision="LONG_BIAS", regime="TREND_UP")
    assert report.sample_count == 120
