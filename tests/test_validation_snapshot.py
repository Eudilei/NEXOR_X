from nexor_x.validation import ValidationSnapshotEngine, ValidationSnapshotInput


def valid_input(**changes):
    data = {
        "paper_trades": 400,
        "profit_factor": 1.35,
        "expected_r": 0.08,
        "drawdown_pct": 10.0,
        "recent_profit_factor": 1.20,
        "recent_expected_r": 0.03,
        "walk_forward_pass_ratio": 0.75,
        "monte_carlo_ruin_probability": 0.02,
        "brier_score_oos": 0.22,
        "calibration_ece_oos": 0.05,
        "integration_healthy": True,
        "recovery_ok": True,
        "supervisor_paper_allowed": True,
        "supervisor_testnet_allowed": True,
        "operational_incidents": 0,
        "critical_test_failures": 0,
    }
    data.update(changes)
    return ValidationSnapshotInput(**data)


def test_ready_for_long_run_validation() -> None:
    report = ValidationSnapshotEngine().evaluate(valid_input())
    assert report.status == "READY_FOR_LONG_RUN_VALIDATION"
    assert report.paper_validation_ready is True
    assert report.testnet_validation_ready is True
    assert report.live_validation_ready is False


def test_low_sample_blocks_validation() -> None:
    report = ValidationSnapshotEngine().evaluate(
        valid_input(paper_trades=50)
    )
    assert report.paper_validation_ready is False
    assert "MINIMUM_PAPER_TRADES" in report.blockers


def test_recovery_failure_blocks_testnet_only() -> None:
    report = ValidationSnapshotEngine().evaluate(
        valid_input(recovery_ok=False)
    )
    assert report.paper_validation_ready is True
    assert report.testnet_validation_ready is False


def test_recent_degradation_blocks_validation() -> None:
    report = ValidationSnapshotEngine().evaluate(
        valid_input(recent_profit_factor=0.8, recent_expected_r=-0.02)
    )
    assert report.paper_validation_ready is False
    assert "RECENT_PROFIT_FACTOR" in report.blockers
    assert "RECENT_EXPECTED_R" in report.blockers


def test_live_always_blocked() -> None:
    report = ValidationSnapshotEngine().evaluate(valid_input())
    assert report.live_validation_ready is False
    assert "LIVE_REMAINS_BLOCKED" in report.warnings
