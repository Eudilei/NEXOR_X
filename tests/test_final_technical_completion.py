from nexor_x.validation.final_completion import (
    FinalTechnicalCompletionGate,
)


def complete_payload():
    return {
        "acceptance_audit": {
            "status": "PASS",
            "passed": True,
            "live_allowed": False,
        },
        "campaign": {
            "status": "COMPLETE",
            "completed": True,
            "progress_percent": 100.0,
            "live_allowed": False,
        },
        "readiness": {
            "candidate_ready": True,
            "live_allowed": False,
        },
        "certification": {
            "evidence_certified": True,
            "live_allowed": False,
        },
    }


def test_all_requirements_complete() -> None:
    report = FinalTechnicalCompletionGate().evaluate(
        **complete_payload()
    )
    assert report["status"] == "TECHNICALLY_COMPLETE"
    assert report["technically_complete"] is True
    assert report["paper_testnet_phase_complete"] is True
    assert report["live_allowed"] is False


def test_campaign_pending() -> None:
    payload = complete_payload()
    payload["campaign"]["status"] = "IN_PROGRESS"
    payload["campaign"]["completed"] = False
    payload["campaign"]["progress_percent"] = 55.0

    report = FinalTechnicalCompletionGate().evaluate(**payload)

    assert report["status"] == "VALIDATION_PENDING"
    assert "validation_campaign_complete" in report[
        "pending_requirements"
    ]


def test_evidence_pending() -> None:
    payload = complete_payload()
    payload["certification"]["evidence_certified"] = False

    report = FinalTechnicalCompletionGate().evaluate(**payload)

    assert report["status"] == "EVIDENCE_PENDING"
    assert "evidence_certified" in report["pending_requirements"]


def test_acceptance_fail_blocks() -> None:
    payload = complete_payload()
    payload["acceptance_audit"]["status"] = "FAIL"
    payload["acceptance_audit"]["passed"] = False

    report = FinalTechnicalCompletionGate().evaluate(**payload)

    assert report["status"] == "BLOCKED"
    assert report["technically_complete"] is False


def test_any_live_allowed_flag_blocks_completion() -> None:
    payload = complete_payload()
    payload["readiness"]["live_allowed"] = True

    report = FinalTechnicalCompletionGate().evaluate(**payload)

    assert report["status"] == "BLOCKED"
    assert "live_still_blocked" in report["pending_requirements"]
    assert report["live_allowed"] is False
