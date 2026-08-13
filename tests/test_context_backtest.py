from nexor_x.pretrade_backtest import (
    ContextBacktestEngine,
    ContextBacktestPolicy,
)


def engine() -> ContextBacktestEngine:
    return ContextBacktestEngine(
        ContextBacktestPolicy(
            minimum_samples=30,
            maximum_samples=300,
            minimum_profit_factor=1.10,
            minimum_expected_r=0.05,
            minimum_recent_profit_factor=1.00,
            minimum_recent_expected_r=0.00,
            maximum_drawdown_r=8.0,
            minimum_walk_forward_pass_ratio=0.60,
            folds=3,
        )
    )


def test_strong_context_is_approved() -> None:
    values = [0.30, 0.20, -0.10, 0.25, -0.05] * 12
    report = engine().evaluate(
        symbol="BTCUSDT",
        decision="LONG_BIAS",
        regime="TREND_UP",
        realized_r=values,
    )
    assert report.approved is True
    assert report.sample_count == 60
    assert report.profit_factor > 1.10
    assert report.expected_r > 0.05
    assert report.live_execution_allowed is False


def test_small_sample_is_blocked() -> None:
    report = engine().evaluate(
        symbol="BTCUSDT",
        decision="LONG_BIAS",
        regime="TREND_UP",
        realized_r=[0.2, -0.1] * 5,
    )
    assert report.approved is False
    assert "MINIMUM_SAMPLES" in report.blockers


def test_negative_context_is_blocked() -> None:
    values = [-0.20, -0.10, 0.05, -0.15, 0.02] * 12
    report = engine().evaluate(
        symbol="ETHUSDT",
        decision="SHORT_BIAS",
        regime="TREND_DOWN",
        realized_r=values,
    )
    assert report.approved is False
    assert "EXPECTED_R" in report.blockers


def test_recent_degradation_blocks_entry() -> None:
    older = [0.30, 0.20, -0.05, 0.25, 0.10] * 10
    recent = [-0.30, -0.20, 0.05, -0.15, 0.02] * 4
    report = engine().evaluate(
        symbol="SOLUSDT",
        decision="LONG_BIAS",
        regime="TREND_UP",
        realized_r=older + recent,
    )
    assert report.approved is False
    assert (
        "RECENT_PROFIT_FACTOR" in report.blockers
        or "RECENT_EXPECTED_R" in report.blockers
    )


def test_large_history_is_capped() -> None:
    values = [0.20, -0.05, 0.15] * 200
    report = engine().evaluate(
        symbol="BNBUSDT",
        decision="LONG_BIAS",
        regime="TREND_UP",
        realized_r=values,
    )
    assert report.sample_count == 300
