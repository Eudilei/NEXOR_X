from nexor_x.operations.live_certification import LiveCertificationEvaluator


def test_certifies_only_evidence_not_live() -> None:
    report = LiveCertificationEvaluator().evaluate(
        readiness={"candidate_ready": True},
        validation_cycle={
            "days_running": 35,
            "closed_trades": 140,
            "profit_factor": 1.45,
            "max_drawdown_pct": 8.0,
        },
        runtime={"live_enabled": False},
    )
    assert report["evidence_certified"] is True
    assert report["live_allowed"] is False
    assert report["live_certified"] is False


def test_insufficient_sample_blocks_certification() -> None:
    report = LiveCertificationEvaluator().evaluate(
        readiness={"candidate_ready": True},
        validation_cycle={
            "days_running": 12,
            "closed_trades": 42,
            "profit_factor": 1.60,
            "max_drawdown_pct": 7.0,
        },
        runtime={"live_enabled": False},
    )
    assert report["evidence_certified"] is False
    assert "minimum_days" in report["blockers"]
    assert "minimum_closed_trades" in report["blockers"]


def test_drawdown_fraction_is_normalized_to_percent() -> None:
    report = LiveCertificationEvaluator().evaluate(
        readiness={"candidate_ready": True},
        validation_cycle={
            "days_running": 30,
            "closed_trades": 100,
            "profit_factor": 1.25,
            "max_drawdown": 0.12,
        },
        runtime={"live_enabled": False},
    )
    assert report["metrics"]["max_drawdown_pct"] == 12.0
    assert report["checks"]["maximum_drawdown"] is True


def test_live_runtime_blocks_evidence_certification() -> None:
    report = LiveCertificationEvaluator().evaluate(
        readiness={"candidate_ready": True},
        validation_cycle={
            "days_running": 40,
            "closed_trades": 200,
            "profit_factor": 1.80,
            "max_drawdown_pct": 5.0,
        },
        runtime={"live_enabled": True},
    )
    assert report["evidence_certified"] is False
    assert "runtime_live_disabled" in report["blockers"]
    assert report["live_allowed"] is False
