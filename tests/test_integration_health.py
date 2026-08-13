from nexor_x.integration import IntegrationHealthEngine, IntegrationHealthInput


def healthy_input(**changes):
    data = {
        "database_ok": True,
        "market_ok": True,
        "scanner_ok": True,
        "strategy_ok": True,
        "allocation_ok": True,
        "recovery_ok": True,
        "supervisor_ok": True,
        "certification_ok": False,
        "update_registry_ok": True,
        "testnet_connector_ok": True,
        "critical_test_failures": 0,
        "operational_incidents": 0,
    }
    data.update(changes)
    return IntegrationHealthInput(**data)


def test_all_core_and_testnet_checks_pass() -> None:
    report = IntegrationHealthEngine().evaluate(healthy_input())
    assert report.status == "INTEGRATION_HEALTHY"
    assert report.paper_ready is True
    assert report.testnet_ready is True
    assert report.live_ready is False


def test_market_failure_blocks_paper_and_testnet() -> None:
    report = IntegrationHealthEngine().evaluate(
        healthy_input(market_ok=False)
    )
    assert report.status == "INTEGRATION_DEGRADED"
    assert report.paper_ready is False
    assert report.testnet_ready is False
    assert "MARKET" in report.blockers


def test_recovery_failure_keeps_paper_but_blocks_testnet() -> None:
    report = IntegrationHealthEngine().evaluate(
        healthy_input(recovery_ok=False)
    )
    assert report.status == "PAPER_HEALTHY_TESTNET_BLOCKED"
    assert report.paper_ready is True
    assert report.testnet_ready is False


def test_incident_blocks_operation() -> None:
    report = IntegrationHealthEngine().evaluate(
        healthy_input(operational_incidents=1)
    )
    assert report.paper_ready is False
    assert "NO_OPERATIONAL_INCIDENTS" in report.blockers


def test_certification_is_warning_and_never_enables_live() -> None:
    report = IntegrationHealthEngine().evaluate(
        healthy_input(certification_ok=True)
    )
    assert report.live_ready is False
    assert "LIVE_REMAINS_BLOCKED" in report.warnings
