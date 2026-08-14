
from nexor_x.operations.filter_rigidity import FilterRigidityMonitor


def test_learning():
    m = FilterRigidityMonitor()
    r = m.record(
        approved=False,
        reasons=[{"name": "rsi", "group": "SCORE"}],
    )
    assert r["status"] == "LEARNING"
    assert r["filter_rejections"]["rsi"] == 1
    assert r["critical_filters_auto_relaxed"] is False


def test_too_rigid():
    m = FilterRigidityMonitor()
    for _ in range(50):
        m.record(
            approved=False,
            reasons=[{"name": "score", "group": "SCORE"}],
        )
    assert m.status()["status"] == "TOO_RIGID"


def test_healthy():
    m = FilterRigidityMonitor()
    for i in range(50):
        m.record(
            approved=i < 10,
            reasons=[] if i < 10 else [{"name": "score", "group": "SCORE"}],
        )
    assert m.status()["status"] == "HEALTHY"
    assert m.status()["approval_percent"] == 20.0


def test_groups():
    m = FilterRigidityMonitor()
    m.record(
        approved=False,
        reasons=[
            {"name": "spread", "group": "CRITICAL"},
            {"name": "regime", "group": "REGIME"},
        ],
    )
    r = m.status()
    assert r["group_rejections"]["CRITICAL"] == 1
    assert r["group_rejections"]["REGIME"] == 1
