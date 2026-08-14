
from nexor_x.operations.filter_decision_telemetry import FilterDecisionTelemetry
from nexor_x.operations.filter_rigidity import FilterRigidityMonitor


def test_classifications():
    t = FilterDecisionTelemetry()
    assert t.classify("entry_reservation_active") == "CRITICAL"
    assert t.classify("regime_mismatch") == "REGIME"
    assert t.classify("rsi_not_confirmed") == "SCORE"


def test_rejected_trace_records_groups():
    monitor = FilterRigidityMonitor()
    t = FilterDecisionTelemetry()
    report = t.record_trace(
        monitor=monitor,
        trace={
            "new_entries_allowed": False,
            "blockers": [
                "entry_reservation_active",
                "regime_mismatch",
            ],
        },
    )
    assert report["evaluated"] == 1
    assert report["rejected"] == 1
    assert report["group_rejections"]["CRITICAL"] == 1
    assert report["group_rejections"]["REGIME"] == 1


def test_approved_trace_records_approved():
    monitor = FilterRigidityMonitor()
    t = FilterDecisionTelemetry()
    report = t.record_trace(
        monitor=monitor,
        trace={
            "new_entries_allowed": True,
            "blockers": [],
        },
    )
    assert report["approved"] == 1
    assert report["rejected"] == 0


def test_telemetry_does_not_relax_filters():
    monitor = FilterRigidityMonitor()
    t = FilterDecisionTelemetry()
    report = t.record_trace(
        monitor=monitor,
        trace={
            "new_entries_allowed": False,
            "blockers": ["drawdown_limit_reached"],
        },
    )
    assert report["critical_filters_auto_relaxed"] is False
    assert report["live_allowed"] is False
