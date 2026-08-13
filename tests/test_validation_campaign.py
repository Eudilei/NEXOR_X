from nexor_x.campaign import ValidationCampaignEngine, ValidationCampaignInput


def valid_input(**changes):
    data = {
        "days_running": 10,
        "paper_trades": 400,
        "profit_factor": 1.35,
        "expected_r": 0.08,
        "drawdown_pct": 8.0,
        "recent_profit_factor": 1.25,
        "recent_expected_r": 0.04,
        "operational_incidents": 0,
        "critical_test_failures": 0,
        "integration_healthy": True,
        "recovery_ok": True,
        "supervisor_paper_allowed": True,
        "supervisor_testnet_allowed": True,
    }
    data.update(changes)
    return ValidationCampaignInput(**data)


def test_validation_continues_before_evidence_milestone() -> None:
    report = ValidationCampaignEngine().evaluate(valid_input())
    assert report.phase == "VALIDATION_IN_PROGRESS"
    assert report.continue_campaign is True
    assert report.live_allowed is False


def test_risk_failure_pauses_campaign() -> None:
    report = ValidationCampaignEngine().evaluate(
        valid_input(drawdown_pct=20.0)
    )
    assert report.phase == "PAUSED_BY_RISK"
    assert report.continue_campaign is False
    assert "DRAWDOWN" in report.blockers


def test_operational_incident_pauses_campaign() -> None:
    report = ValidationCampaignEngine().evaluate(
        valid_input(operational_incidents=1)
    )
    assert report.phase == "PAUSED_BY_RISK"
    assert "NO_OPERATIONAL_INCIDENTS" in report.blockers


def test_evidence_milestone_requires_cqo_review() -> None:
    report = ValidationCampaignEngine().evaluate(
        valid_input(
            days_running=35,
            paper_trades=1200,
            profit_factor=1.55,
            expected_r=0.10,
            recent_profit_factor=1.30,
            recent_expected_r=0.05,
        )
    )
    assert report.phase == "EVIDENCE_MILESTONE_REACHED"
    assert report.continue_campaign is False
    assert "CQO_REVIEW_REQUIRED" in report.warnings
    assert report.live_allowed is False


def test_recovery_failure_blocks_testnet_and_pauses() -> None:
    report = ValidationCampaignEngine().evaluate(
        valid_input(recovery_ok=False)
    )
    assert report.testnet_allowed is False
    assert report.phase == "PAUSED_BY_RISK"
