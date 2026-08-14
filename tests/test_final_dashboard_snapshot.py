from nexor_x.validation.final_dashboard import (
    FinalTechnicalDashboardSnapshot,
)


def test_complete_snapshot() -> None:
    report = FinalTechnicalDashboardSnapshot().build(
        completion={
            "status": "TECHNICALLY_COMPLETE",
            "technically_complete": True,
            "paper_testnet_phase_complete": True,
            "candidate_ready": True,
            "evidence_certified": True,
            "pending_requirements": [],
        },
        campaign={
            "status": "COMPLETE",
            "progress_percent": 100.0,
            "valid_passes": 20,
            "required_passes": 20,
        },
        acceptance={"status": "PASS"},
        readiness_summary={
            "blockers": [],
            "warnings": [],
            "exposure_multiplier": 1.0,
        },
    )

    assert report["technically_complete"] is True
    assert report["validation_progress_percent"] == 100.0
    assert report["live_allowed"] is False
    assert report["live_label"] == "BLOQUEADO"


def test_pending_snapshot_preserves_reasons() -> None:
    report = FinalTechnicalDashboardSnapshot().build(
        completion={
            "status": "VALIDATION_PENDING",
            "technically_complete": False,
            "paper_testnet_phase_complete": False,
            "candidate_ready": True,
            "evidence_certified": False,
            "pending_requirements": [
                "validation_campaign_complete",
                "evidence_certified",
            ],
        },
        campaign={
            "status": "IN_PROGRESS",
            "progress_percent": 40.0,
            "valid_passes": 8,
            "required_passes": 20,
        },
        acceptance={"status": "PASS"},
        readiness_summary={
            "blockers": ["evidence_pending"],
            "warnings": ["post_recovery_probation_active"],
            "exposure_multiplier": 0.25,
        },
    )

    assert report["status"] == "VALIDATION_PENDING"
    assert "validation_campaign_complete" in report[
        "pending_requirements"
    ]
    assert report["exposure_multiplier"] == 0.25
    assert report["live_certified"] is False


def test_snapshot_is_read_only() -> None:
    report = FinalTechnicalDashboardSnapshot().build(
        completion={},
        campaign={},
        acceptance={},
        readiness_summary={},
    )
    assert report["read_only"] is True
    assert report["live_allowed"] is False
