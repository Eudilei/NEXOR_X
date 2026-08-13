from nexor_x.operations.operational_acceptance_audit import (
    OperationalAcceptanceAudit,
)


def healthy():
    return {
        "readiness": {
            "candidate_ready": True,
            "live_allowed": False,
        },
        "certification": {
            "evidence_certified": True,
            "live_allowed": False,
        },
        "degradation": {
            "state": "NORMAL",
        },
        "entry_trace": {
            "new_entries_allowed": True,
            "blockers": [],
            "read_only": True,
            "live_allowed": False,
        },
        "summary": {
            "paper_testnet_new_entries_allowed": True,
            "blockers": [],
            "exposure_multiplier": 1.0,
            "read_only": True,
            "live_allowed": False,
            "live_certified": False,
        },
    }


def test_healthy_system_passes() -> None:
    report = OperationalAcceptanceAudit().run(**healthy())
    assert report["status"] == "PASS"
    assert report["passed"] is True
    assert report["failed_checks"] == []


def test_live_flag_breaks_audit() -> None:
    payload = healthy()
    payload["summary"]["live_allowed"] = True

    report = OperationalAcceptanceAudit().run(**payload)

    assert report["status"] == "FAIL"
    assert "live_blocked_summary" in report["failed_checks"]


def test_blocked_degradation_must_block_entry() -> None:
    payload = healthy()
    payload["degradation"]["state"] = "BLOCKED"
    payload["entry_trace"]["new_entries_allowed"] = True
    payload["summary"]["paper_testnet_new_entries_allowed"] = True

    report = OperationalAcceptanceAudit().run(**payload)

    assert report["status"] == "FAIL"
    assert "blocked_degradation_blocks_entry" in report["failed_checks"]
    assert "blocked_degradation_blocks_summary" in report["failed_checks"]


def test_entry_blockers_must_reach_summary() -> None:
    payload = healthy()
    payload["entry_trace"]["new_entries_allowed"] = False
    payload["entry_trace"]["blockers"] = ["entry_reservation_active"]
    payload["summary"]["paper_testnet_new_entries_allowed"] = False

    report = OperationalAcceptanceAudit().run(**payload)

    assert report["status"] == "FAIL"
    assert "entry_blockers_propagated_to_summary" in report["failed_checks"]


def test_invalid_exposure_multiplier_fails() -> None:
    payload = healthy()
    payload["summary"]["exposure_multiplier"] = 1.5

    report = OperationalAcceptanceAudit().run(**payload)

    assert report["status"] == "FAIL"
    assert "exposure_multiplier_valid" in report["failed_checks"]


def test_certification_cannot_exist_without_readiness() -> None:
    payload = healthy()
    payload["readiness"]["candidate_ready"] = False
    payload["certification"]["evidence_certified"] = True

    report = OperationalAcceptanceAudit().run(**payload)

    assert report["status"] == "FAIL"
    assert "certification_requires_readiness" in report["failed_checks"]
