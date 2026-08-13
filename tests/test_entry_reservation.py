from datetime import UTC, datetime, timedelta
from nexor_x.operations.entry_reservation import AtomicEntryReservationGuard


def test_first_reservation_allowed(tmp_path):
    g = AtomicEntryReservationGuard(state_path=tmp_path / "r.json")
    r = g.reserve(action="PAPER_OPEN")
    assert r["allowed"] is True
    assert r["reservation_id"]


def test_second_reservation_blocked(tmp_path):
    g = AtomicEntryReservationGuard(state_path=tmp_path / "r.json")
    g.reserve(action="PAPER_OPEN")
    r = g.reserve(action="TESTNET_CREATE")
    assert r["allowed"] is False
    assert r["reason"] == "ENTRY_RESERVATION_ALREADY_ACTIVE"


def test_confirm_clears(tmp_path):
    g = AtomicEntryReservationGuard(state_path=tmp_path / "r.json")
    r = g.reserve(action="PAPER_OPEN")
    c = g.confirm(r["reservation_id"])
    assert c["confirmed"] is True
    assert g.status()["active"] is False


def test_release_clears(tmp_path):
    g = AtomicEntryReservationGuard(state_path=tmp_path / "r.json")
    r = g.reserve(action="PAPER_OPEN")
    x = g.release(r["reservation_id"])
    assert x["released"] is True
    assert g.status()["active"] is False


def test_expiry_allows_new_reservation(tmp_path):
    g = AtomicEntryReservationGuard(state_path=tmp_path / "r.json")
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    first = g.reserve(action="PAPER_OPEN", now=t0)
    second = g.reserve(action="PAPER_OPEN", now=t0 + timedelta(seconds=31))
    assert second["allowed"] is True
    assert second["reservation_id"] != first["reservation_id"]


def test_persisted_state_survives_restart(tmp_path):
    path = tmp_path / "r.json"
    g1 = AtomicEntryReservationGuard(state_path=path)
    r = g1.reserve(action="PAPER_OPEN")
    g2 = AtomicEntryReservationGuard(state_path=path)
    s = g2.status()
    assert s["active"] is True
    assert s["reservation_id"] == r["reservation_id"]
