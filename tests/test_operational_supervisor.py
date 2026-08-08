from nexor_x.supervisor import OperationalSupervisor, SupervisorInputs


def base_inputs(**changes):
    data = {
        "mode": "PAPER",
        "recovery_ok": True,
        "exchange_ready": True,
        "certification_passed": False,
        "live_connector_tested": True,
        "data_freshness_ok": True,
        "hard_stop_active": False,
        "critical_test_failures": 0,
        "operational_incidents": 0,
    }
    data.update(changes)
    return SupervisorInputs(**data)


def test_clean_system_allows_paper_and_testnet_but_never_live() -> None:
    decision = OperationalSupervisor().evaluate(base_inputs())
    assert decision.status == "PAPER_AND_TESTNET_READY"
    assert decision.paper_allowed is True
    assert decision.testnet_allowed is True
    assert decision.live_allowed is False


def test_recovery_failure_keeps_paper_but_blocks_testnet() -> None:
    decision = OperationalSupervisor().evaluate(
        base_inputs(recovery_ok=False)
    )
    assert decision.status == "PAPER_ONLY"
    assert decision.paper_allowed is True
    assert decision.testnet_allowed is False
    assert "RECOVERY_NOT_CLEAN" in decision.blockers


def test_hard_stop_locks_every_operational_mode() -> None:
    decision = OperationalSupervisor().evaluate(
        base_inputs(hard_stop_active=True)
    )
    assert decision.status == "LOCKED"
    assert decision.paper_allowed is False
    assert decision.testnet_allowed is False
    assert decision.live_allowed is False


def test_live_request_is_ignored_even_when_certified() -> None:
    decision = OperationalSupervisor().evaluate(
        base_inputs(mode="LIVE", certification_passed=True)
    )
    assert decision.live_allowed is False
    assert "LIVE_MODE_REQUEST_IGNORED" in decision.warnings
    assert "CERTIFICATION_DOES_NOT_ENABLE_LIVE" in decision.warnings


def test_stale_data_blocks_paper_and_testnet() -> None:
    decision = OperationalSupervisor().evaluate(
        base_inputs(data_freshness_ok=False)
    )
    assert decision.paper_allowed is False
    assert decision.testnet_allowed is False
    assert "STALE_MARKET_DATA" in decision.blockers
