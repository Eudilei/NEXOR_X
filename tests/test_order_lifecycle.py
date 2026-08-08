from __future__ import annotations

from types import SimpleNamespace

import pytest

from nexor_x.orders import TestnetOrderLifecycleService


class FakeConnector:
    def __init__(self, *, testnet: bool = True) -> None:
        self.policy = SimpleNamespace(use_testnet=testnet)

    async def get_testnet_order(self, **kwargs):
        return {
            "symbol": kwargs["symbol"],
            "clientOrderId": kwargs.get("client_order_id") or "NX-1",
            "orderId": 42,
            "status": "PARTIALLY_FILLED",
            "executedQty": "0.005",
            "avgPrice": "62000.0",
            "reduceOnly": False,
            "updateTime": 1_700_000_000_000,
        }

    async def cancel_testnet_order(self, **kwargs):
        return {
            "symbol": kwargs["symbol"],
            "clientOrderId": kwargs.get("client_order_id") or "NX-1",
            "orderId": 42,
            "status": "CANCELED",
        }


@pytest.mark.asyncio
async def test_status_snapshot() -> None:
    service = TestnetOrderLifecycleService(FakeConnector())
    result = await service.status(
        symbol="BTCUSDT",
        client_order_id="NX-1",
    )
    assert result["order"]["status"] == "PARTIALLY_FILLED"
    assert result["order"]["executed_quantity"] == 0.005
    assert result["live_order_sent"] is False


@pytest.mark.asyncio
async def test_cancel_testnet_order() -> None:
    service = TestnetOrderLifecycleService(FakeConnector())
    result = await service.cancel(
        symbol="BTCUSDT",
        client_order_id="NX-1",
    )
    assert result["status"] == "CANCELED"
    assert result["testnet"] is True


@pytest.mark.asyncio
async def test_non_testnet_is_rejected() -> None:
    service = TestnetOrderLifecycleService(FakeConnector(testnet=False))
    with pytest.raises(RuntimeError):
        await service.status(
            symbol="BTCUSDT",
            client_order_id="NX-1",
        )
