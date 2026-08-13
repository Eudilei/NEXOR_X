
from nexor_x.operations.operational_readiness_summary import (
    UnifiedOperationalReadinessSummary,
)


def healthy_payload():
    return {
        "readiness": {"candidate_ready": True, "blockers": []},
        "certification": {"evidence_certified": True, "blockers": []},
        "degradation": {
            "state": "NORMAL",
            "hard_reasons": [],
            "caution_reasons": [],
        },
        "entry_trace": {
            "status": "ENTRY_ALLOWED",
            "new_entries_allowed": True,
            "blockers": [],
            "warnings": [],
            "exposure_multiplier": 1.0,
        },
    }


def test_ready():
    r = UnifiedOperationalReadinessSummary().build(**healthy_payload())
    assert r["overall_status"] == "READY"
    assert r["paper_testnet_new_entries_allowed"] is True
    assert r["live_allowed"] is False


def test_readiness_blocker():
    p = healthy_payload()
    p["readiness"] = {
        "candidate_ready": False,
        "blockers": ["credentials_configured"],
    }
    r = UnifiedOperationalReadinessSummary().build(**p)
    assert r["overall_status"] == "BLOCKED"
    assert "credentials_configured" in r["blockers"]


def test_degradation_block():
    p = healthy_payload()
    p["degradation"] = {
        "state": "BLOCKED",
        "hard_reasons": ["drawdown_limit_reached"],
        "caution_reasons": [],
    }
    r = UnifiedOperationalReadinessSummary().build(**p)
    assert r["paper_testnet_new_entries_allowed"] is False
    assert "drawdown_limit_reached" in r["blockers"]


def test_warning_becomes_caution():
    p = healthy_payload()
    p["entry_trace"]["warnings"] = ["post_recovery_probation_active"]
    p["entry_trace"]["exposure_multiplier"] = 0.25
    r = UnifiedOperationalReadinessSummary().build(**p)
    assert r["overall_status"] == "CAUTION"
    assert r["exposure_multiplier"] == 0.25


def test_entry_reservation_blocker():
    p = healthy_payload()
    p["entry_trace"] = {
        "status": "ENTRY_BLOCKED",
        "new_entries_allowed": False,
        "blockers": ["entry_reservation_active"],
        "warnings": [],
        "exposure_multiplier": 1.0,
    }
    r = UnifiedOperationalReadinessSummary().build(**p)
    assert r["overall_status"] == "BLOCKED"
    assert "entry_reservation_active" in r["blockers"]
