from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from nexor_x.infrastructure.database import DatabaseService
from nexor_x.orders import (
    OrderSide,
    OrderType,
    TestnetOrderRequest,
    TestnetOrderService,
)


class FakeConnector:
    def __init__(self, *, testnet: bool = True) -> None:
        self.policy = SimpleNamespace(use_testnet=testnet)
        self.calls = 0

    async def create_testnet_order(self, **kwargs):
        self.calls += 1
        return {
            "orderId": 12345,
            "status": "NEW",
            **kwargs,
        }


@pytest.mark.asyncio
async def test_duplicate_intent_is_not_sent_twice(tmp_path: Path) -> None:
    database = DatabaseService(tmp_path / "orders.db")
    await database.start()
    try:
        connector = FakeConnector()
        service = TestnetOrderService(database, connector)
        await service.start()
        request = TestnetOrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.01,
        )
        first = await service.create(
            strategy_id="trend_pullback",
            signal_id="signal-001",
            request=request,
        )
        second = await service.create(
            strategy_id="trend_pullback",
            signal_id="signal-001",
            request=request,
        )
        assert connector.calls == 1
        assert first["duplicate"] is False
        assert second["duplicate"] is True
        assert first["idempotency_key"] == second["idempotency_key"]
        assert first["live_order_sent"] is False
    finally:
        await database.stop()


@pytest.mark.asyncio
async def test_non_testnet_connector_is_rejected(tmp_path: Path) -> None:
    database = DatabaseService(tmp_path / "orders.db")
    await database.start()
    try:
        service = TestnetOrderService(database, FakeConnector(testnet=False))
        request = TestnetOrderRequest(
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )
        with pytest.raises(RuntimeError):
            await service.create(
                strategy_id="momentum",
                signal_id="signal-002",
                request=request,
            )
    finally:
        await database.stop()


def test_market_order_rejects_price() -> None:
    request = TestnetOrderRequest(
        symbol="SOLUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1.0,
        price=100.0,
    )
    with pytest.raises(ValueError):
        request.normalized()


def test_limit_order_requires_price() -> None:
    request = TestnetOrderRequest(
        symbol="SOLUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=1.0,
    )
    with pytest.raises(ValueError):
        request.normalized()
