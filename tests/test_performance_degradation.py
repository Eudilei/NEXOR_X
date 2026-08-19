from nexor_x.operations.performance_degradation import PerformanceDegradationGuard


def test_normal_performance_allows_entries() -> None:
    report = PerformanceDegradationGuard().evaluate(
        recent={
            "recent_trades": 30,
            "profit_factor": 1.55,
            "drawdown_pct": 5.0,
            "loss_streak": 1,
        },
        certification={"evidence_certified": True},
    )
    assert report["state"] == "NORMAL"
    assert report["new_entries_allowed"] is True
    assert report["manage_existing_positions"] is True
    assert report["live_allowed"] is False


def test_weak_pf_enters_caution_but_does_not_block() -> None:
    report = PerformanceDegradationGuard().evaluate(
        recent={
            "recent_trades": 25,
            "profit_factor": 1.10,
            "drawdown_pct": 4.0,
            "loss_streak": 2,
        },
        certification={"evidence_certified": True},
    )
    assert report["state"] == "CAUTION"
    assert report["new_entries_allowed"] is True
    assert "profit_factor_weak" in report["caution_reasons"]


def test_pf_below_one_blocks_new_entries() -> None:
    report = PerformanceDegradationGuard().evaluate(
        recent={
            "recent_trades": 25,
            "profit_factor": 0.92,
            "drawdown_pct": 6.0,
            "loss_streak": 2,
        },
        certification={"evidence_certified": True},
    )
    assert report["state"] == "BLOCKED"
    assert report["new_entries_allowed"] is False
    assert report["manage_existing_positions"] is True
    assert "profit_factor_below_1" in report["hard_reasons"]


def test_drawdown_limit_blocks_entries() -> None:
    report = PerformanceDegradationGuard().evaluate(
        recent={
            "recent_trades": 40,
            "profit_factor": 1.30,
            "drawdown_pct": 15.5,
            "loss_streak": 2,
        },
        certification={"evidence_certified": True},
    )
    assert report["state"] == "BLOCKED"
    assert "drawdown_limit_reached" in report["hard_reasons"]


def test_loss_streak_blocks_even_before_minimum_sample() -> None:
    report = PerformanceDegradationGuard().evaluate(
        recent={
            "recent_trades": 8,
            "profit_factor": 0.80,
            "drawdown_pct": 3.0,
            "loss_streak": 6,
        },
        certification={"evidence_certified": True},
    )
    assert report["metrics"]["enough_sample"] is False
    assert report["state"] == "BLOCKED"
    assert "loss_streak_critical" in report["hard_reasons"]


def test_fractional_drawdown_is_normalized() -> None:
    report = PerformanceDegradationGuard().evaluate(
        recent={
            "recent_trades": 30,
            "profit_factor": 1.40,
            "max_drawdown": 0.11,
            "loss_streak": 1,
        },
        certification={"evidence_certified": True},
    )
    assert report["metrics"]["drawdown_pct"] == 11.0
    assert report["state"] == "CAUTION"


def test_healthy_shadow_can_start_controlled_recovery() -> None:
    report = PerformanceDegradationGuard().evaluate(
        recent={
            "recent_trades": 25,
            "recent_profit_factor": 0.90,
            "drawdown_pct": 8.0,
            "loss_streak": 6,
            "recent_shadow_samples": 40,
            "recent_shadow_profit_factor": 1.45,
            "recent_shadow_expected_r": 0.12,
        },
        certification={"evidence_certified": True},
    )
    assert report["state"] == "NORMAL"
    assert report["new_entries_allowed"] is True
    assert "shadow_recovery_confirmed" in report["recovery_reasons"]


def test_shadow_never_overrides_drawdown_hard_stop() -> None:
    report = PerformanceDegradationGuard().evaluate(
        recent={
            "recent_trades": 25,
            "recent_profit_factor": 0.90,
            "drawdown_pct": 16.0,
            "loss_streak": 6,
            "recent_shadow_samples": 100,
            "recent_shadow_profit_factor": 2.0,
            "recent_shadow_expected_r": 0.3,
        },
        certification={"evidence_certified": True},
    )
    assert report["state"] == "BLOCKED"
    assert "drawdown_limit_reached" in report["hard_reasons"]
