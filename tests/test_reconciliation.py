from decimal import Decimal

from nexor_x.exchange import PositionSnapshot, ReconciliationService


def position(symbol: str, quantity: str, direction: str = "LONG") -> PositionSnapshot:
    return PositionSnapshot(
        symbol=symbol,
        direction=direction,
        quantity=Decimal(quantity),
        entry_price=Decimal("100"),
    )


def test_matching_positions_pass() -> None:
    report = ReconciliationService().reconcile(
        [position("BTCUSDT", "0.01")],
        [position("BTCUSDT", "0.01")],
    )
    assert report.reconciliation_ok is True
    assert report.status == "MATCHED"
    assert report.execution_allowed is False


def test_exchange_only_position_is_detected() -> None:
    report = ReconciliationService().reconcile(
        [],
        [position("ETHUSDT", "0.2")],
    )
    assert report.reconciliation_ok is False
    assert report.exchange_only_positions == 1
    assert report.issues[0].issue_type == "EXCHANGE_ONLY_POSITION"


def test_quantity_mismatch_is_detected() -> None:
    report = ReconciliationService().reconcile(
        [position("SOLUSDT", "2.0")],
        [position("SOLUSDT", "1.5")],
    )
    assert report.quantity_mismatches == 1
    assert report.issues[0].issue_type == "QUANTITY_MISMATCH"
