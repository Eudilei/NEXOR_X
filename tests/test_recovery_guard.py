from __future__ import annotations

from decimal import Decimal

from nexor_x.recovery.service import RecoveryGuardService


def test_position_mismatch_detected() -> None:
    local = {("BTCUSDT", "LONG"): Decimal("0.01")}
    exchange = {("BTCUSDT", "LONG"): Decimal("0.02")}
    issues = RecoveryGuardService._position_issues(local, exchange)
    assert len(issues) == 1
    assert issues[0].issue_type == "POSITION_QUANTITY_MISMATCH"


def test_exchange_only_position_detected() -> None:
    local = {}
    exchange = {("ETHUSDT", "SHORT"): Decimal("0.5")}
    issues = RecoveryGuardService._position_issues(local, exchange)
    assert issues[0].issue_type == "EXCHANGE_ONLY_POSITION"


def test_matching_positions_clean() -> None:
    local = {("SOLUSDT", "LONG"): Decimal("2")}
    exchange = {("SOLUSDT", "LONG"): Decimal("2")}
    assert RecoveryGuardService._position_issues(local, exchange) == []


def test_exchange_position_normalization() -> None:
    normalized = RecoveryGuardService._normalize_exchange_positions(
        [
            {"symbol": "BTCUSDT", "positionAmt": "0.01"},
            {"symbol": "ETHUSDT", "positionAmt": "-0.50"},
            {"symbol": "XRPUSDT", "positionAmt": "0"},
        ]
    )
    assert normalized[("BTCUSDT", "LONG")] == Decimal("0.01")
    assert normalized[("ETHUSDT", "SHORT")] == Decimal("0.50")
    assert ("XRPUSDT", "LONG") not in normalized


def test_order_divergence_detected() -> None:
    local = {
        "NX-LOCAL": {
            "client_order_id": "NX-LOCAL",
            "exchange_order_id": "",
            "status": "NEW",
            "payload_json": (
                '{"request":{"symbol":"BTCUSDT"}}'
            ),
        }
    }
    exchange = {
        "NX-EXCHANGE": {
            "clientOrderId": "NX-EXCHANGE",
            "symbol": "ETHUSDT",
            "status": "NEW",
        }
    }
    issues = RecoveryGuardService._order_issues(local, exchange)
    kinds = {item.issue_type for item in issues}
    assert "LOCAL_ONLY_PENDING_ORDER" in kinds
    assert "EXCHANGE_ONLY_OPEN_ORDER" in kinds
