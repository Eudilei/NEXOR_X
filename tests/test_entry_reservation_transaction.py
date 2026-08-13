
import pytest

from nexor_x.operations.entry_reservation import AtomicEntryReservationGuard


def test_transaction_confirms_on_success(tmp_path) -> None:
    guard = AtomicEntryReservationGuard(
        state_path=tmp_path / "reservation.json"
    )

    with guard.transaction(
        action="PAPER_OPEN",
        metadata={"symbol": "BTCUSDT"},
    ) as reservation:
        assert reservation["allowed"] is True
        assert guard.status()["active"] is True

    assert guard.status()["active"] is False


def test_transaction_releases_on_exception(tmp_path) -> None:
    guard = AtomicEntryReservationGuard(
        state_path=tmp_path / "reservation.json"
    )

    with pytest.raises(RuntimeError, match="boom"):
        with guard.transaction(action="PAPER_OPEN"):
            assert guard.status()["active"] is True
            raise RuntimeError("boom")

    assert guard.status()["active"] is False


def test_concurrent_second_transaction_is_blocked(tmp_path) -> None:
    guard = AtomicEntryReservationGuard(
        state_path=tmp_path / "reservation.json"
    )

    with guard.transaction(action="PAPER_OPEN"):
        with pytest.raises(RuntimeError, match="active atomic reservation"):
            with guard.transaction(action="TESTNET_CREATE"):
                pass


def test_reduce_only_bypass_does_not_create_reservation(tmp_path) -> None:
    guard = AtomicEntryReservationGuard(
        state_path=tmp_path / "reservation.json"
    )

    with guard.transaction(
        action="TESTNET_CREATE",
        bypass=True,
    ) as reservation:
        assert reservation["bypass"] is True
        assert guard.status()["active"] is False

    assert guard.status()["active"] is False


def test_early_return_style_still_confirms(tmp_path) -> None:
    guard = AtomicEntryReservationGuard(
        state_path=tmp_path / "reservation.json"
    )

    def operation() -> str:
        with guard.transaction(action="PAPER_OPEN"):
            return "ok"

    assert operation() == "ok"
    assert guard.status()["active"] is False
