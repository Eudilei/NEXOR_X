
from nexor_x.operations.entry_decision_trace import UnifiedEntryDecisionTrace


def base():
    return {
        "degradation": {
            "state": "NORMAL",
            "new_entries_allowed": True,
            "hard_reasons": [],
            "caution_reasons": [],
        },
        "recovery": {"latched": False, "healthy_checks": 0},
        "probation": {"active": False, "admitted_entries": 0},
        "exposure": {"exposure_multiplier": 1.0},
        "reservation": {"active": False},
    }


def test_normal_path_allowed():
    r = UnifiedEntryDecisionTrace().build(**base())
    assert r["status"] == "ENTRY_ALLOWED"
    assert r["new_entries_allowed"] is True
    assert r["read_only"] is True
    assert r["live_allowed"] is False


def test_degradation_block_explained():
    p = base()
    p["degradation"] = {
        "state": "BLOCKED",
        "new_entries_allowed": False,
        "hard_reasons": ["profit_factor_below_1"],
    }
    r = UnifiedEntryDecisionTrace().build(**p)
    assert r["new_entries_allowed"] is False
    assert "profit_factor_below_1" in r["blockers"]


def test_recovery_latch_blocks():
    p = base()
    p["recovery"]["latched"] = True
    r = UnifiedEntryDecisionTrace().build(**p)
    assert "recovery_hysteresis_active" in r["blockers"]


def test_reservation_blocks():
    p = base()
    p["reservation"]["active"] = True
    r = UnifiedEntryDecisionTrace().build(**p)
    assert "entry_reservation_active" in r["blockers"]


def test_probation_warning_and_exposure_visible():
    p = base()
    p["probation"]["active"] = True
    p["exposure"]["exposure_multiplier"] = 0.25
    r = UnifiedEntryDecisionTrace().build(**p)
    assert "post_recovery_probation_active" in r["warnings"]
    assert r["exposure_percent"] == 25.0
