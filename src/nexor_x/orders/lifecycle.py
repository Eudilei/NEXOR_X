from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class OrderStatusSnapshot:
    symbol: str
    client_order_id: str
    exchange_order_id: str | None
    status: str
    executed_quantity: float
    average_price: float | None
    reduce_only: bool
    update_time: datetime

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["update_time"] = self.update_time.isoformat()
        return data


class TestnetOrderLifecycleService:
    """Read/cancel lifecycle for TESTNET orders only."""

    def __init__(self, connector: Any) -> None:
        self.connector = connector

    def _ensure_testnet(self) -> None:
        if not getattr(self.connector.policy, "use_testnet", False):
            raise RuntimeError("Order lifecycle is restricted to TESTNET")

    async def status(
        self,
        *,
        symbol: str,
        client_order_id: str | None = None,
        exchange_order_id: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_testnet()
        if not client_order_id and not exchange_order_id:
            raise ValueError("client_order_id or exchange_order_id is required")

        payload = await self.connector.get_testnet_order(
            symbol=symbol.strip().upper(),
            client_order_id=client_order_id,
            exchange_order_id=exchange_order_id,
        )
        snapshot = OrderStatusSnapshot(
            symbol=str(payload["symbol"]),
            client_order_id=str(payload.get("clientOrderId") or ""),
            exchange_order_id=(
                None if payload.get("orderId") is None else str(payload["orderId"])
            ),
            status=str(payload.get("status", "UNKNOWN")),
            executed_quantity=float(payload.get("executedQty") or 0.0),
            average_price=(
                None
                if payload.get("avgPrice") in (None, "", "0", 0, 0.0)
                else float(payload["avgPrice"])
            ),
            reduce_only=bool(payload.get("reduceOnly", False)),
            update_time=datetime.fromtimestamp(
                float(payload.get("updateTime") or payload.get("time") or 0) / 1000,
                tz=UTC,
            ),
        )
        return {
            "status": "OK",
            "order": snapshot.to_dict(),
            "testnet": True,
            "live_order_sent": False,
        }

    async def cancel(
        self,
        *,
        symbol: str,
        client_order_id: str | None = None,
        exchange_order_id: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_testnet()
        if not client_order_id and not exchange_order_id:
            raise ValueError("client_order_id or exchange_order_id is required")

        payload = await self.connector.cancel_testnet_order(
            symbol=symbol.strip().upper(),
            client_order_id=client_order_id,
            exchange_order_id=exchange_order_id,
        )
        return {
            "status": str(payload.get("status", "CANCELED")),
            "symbol": str(payload.get("symbol") or symbol).upper(),
            "client_order_id": str(payload.get("clientOrderId") or client_order_id or ""),
            "exchange_order_id": (
                None if payload.get("orderId") is None else str(payload["orderId"])
            ),
            "testnet": True,
            "live_order_sent": False,
        }
