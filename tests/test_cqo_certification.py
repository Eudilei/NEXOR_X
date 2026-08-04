from nexor_x.certification import (
    CQOCertificationEngine,
    CertificationEvidence,
    CertificationPolicy,
)


def valid_evidence(**overrides):
    data = {
        "paper_trades": 1500,
        "profit_factor": 1.55,
        "expected_r": 0.12,
        "maximum_drawdown_pct": 9.0,
        "walk_forward_pass_ratio": 0.80,
        "monte_carlo_ruin_probability": 0.01,
        "brier_score_oos": 0.20,
        "calibration_ece_oos": 0.04,
        "operational_incidents": 0,
        "critical_test_failures": 0,
        "days_in_paper": 45,
        "recent_profit_factor": 1.30,
        "recent_expected_r": 0.05,
        "data_freshness_ok": True,
        "reconciliation_ok": True,
        "secrets_configured": True,
        "live_connector_tested": True,
        "manual_owner_approval": False,
    }
    data.update(overrides)
    return CertificationEvidence(**data)


def test_technical_pass_still_blocks_live() -> None:
    result = CQOCertificationEngine().evaluate(valid_evidence())
    assert result.passed is True
    assert result.status == "TECHNICALLY_APPROVED_MANUAL_APPROVAL_REQUIRED"
    assert result.live_execution_allowed is False
    assert "MANUAL_OWNER_APPROVAL_PENDING" in result.warnings


def test_manual_approval_does_not_switch_mode() -> None:
    result = CQOCertificationEngine().evaluate(
        valid_evidence(manual_owner_approval=True)
    )
    assert result.status == "CERTIFIED_PENDING_MODE_SWITCH"
    assert result.live_execution_allowed is False
    assert result.requires_manual_approval is False


def test_rejects_insufficient_sample() -> None:
    result = CQOCertificationEngine().evaluate(valid_evidence(paper_trades=200))
    assert result.passed is False
    assert "MINIMUM_PAPER_TRADES" in result.blockers


def test_rejects_recent_degradation() -> None:
    result = CQOCertificationEngine().evaluate(
        valid_evidence(recent_profit_factor=0.90, recent_expected_r=-0.02)
    )
    assert result.passed is False
    assert "RECENT_PROFIT_FACTOR" in result.blockers
    assert "RECENT_EXPECTED_R" in result.blockers


def test_rejects_operational_weakness() -> None:
    result = CQOCertificationEngine().evaluate(
        valid_evidence(
            operational_incidents=1,
            reconciliation_ok=False,
            live_connector_tested=False,
        )
    )
    assert result.passed is False
    assert "NO_OPERATIONAL_INCIDENTS" in result.blockers
    assert "RECONCILIATION" in result.blockers
    assert "LIVE_CONNECTOR_TESTED" in result.blockers
