from nexor_x.validation.release_candidate import ReleaseCandidateAudit


def components():
    return {
        name: True
        for name in ReleaseCandidateAudit.REQUIRED_COMPONENTS
    }


def test_all_checks_yield_rc_ready() -> None:
    report = ReleaseCandidateAudit().evaluate(
        acceptance={
            "status": "PASS",
            "passed": True,
            "live_allowed": False,
        },
        final_snapshot={
            "status": "VALIDATION_PENDING",
            "read_only": True,
            "live_allowed": False,
            "live_certified": False,
            "validation_progress_percent": 45.0,
            "candidate_ready": True,
            "evidence_certified": False,
        },
        component_presence=components(),
        version="0.56.0",
    )

    assert report["status"] == "RC_READY"
    assert report["rc_ready"] is True
    assert report["architecture_frozen"] is True
    assert report["live_allowed"] is False


def test_missing_component_blocks_rc() -> None:
    present = components()
    present["entry_reservation"] = False

    report = ReleaseCandidateAudit().evaluate(
        acceptance={
            "status": "PASS",
            "passed": True,
            "live_allowed": False,
        },
        final_snapshot={
            "read_only": True,
            "live_allowed": False,
            "live_certified": False,
        },
        component_presence=present,
        version="0.56.0",
    )

    assert report["status"] == "RC_BLOCKED"
    assert "entry_reservation" in report["missing_components"]


def test_acceptance_fail_blocks_rc() -> None:
    report = ReleaseCandidateAudit().evaluate(
        acceptance={
            "status": "FAIL",
            "passed": False,
            "live_allowed": False,
        },
        final_snapshot={
            "read_only": True,
            "live_allowed": False,
            "live_certified": False,
        },
        component_presence=components(),
        version="0.56.0",
    )

    assert report["rc_ready"] is False
    assert "acceptance_audit_passed" in report["failed_checks"]


def test_any_live_flag_blocks_rc() -> None:
    report = ReleaseCandidateAudit().evaluate(
        acceptance={
            "status": "PASS",
            "passed": True,
            "live_allowed": False,
        },
        final_snapshot={
            "read_only": True,
            "live_allowed": True,
            "live_certified": False,
        },
        component_presence=components(),
        version="0.56.0",
    )

    assert report["status"] == "RC_BLOCKED"
    assert "snapshot_live_blocked" in report["failed_checks"]


def test_evidence_can_still_be_pending_at_rc_stage() -> None:
    report = ReleaseCandidateAudit().evaluate(
        acceptance={
            "status": "PASS",
            "passed": True,
            "live_allowed": False,
        },
        final_snapshot={
            "status": "EVIDENCE_PENDING",
            "read_only": True,
            "live_allowed": False,
            "live_certified": False,
            "candidate_ready": True,
            "evidence_certified": False,
        },
        component_presence=components(),
        version="0.56.0",
    )

    assert report["rc_ready"] is True
    assert report["evidence_certified"] is False
