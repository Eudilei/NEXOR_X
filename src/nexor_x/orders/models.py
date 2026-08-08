from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


@dataclass(frozen=True, slots=True)
class TestnetOrderRequest:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: float | None = None
    reduce_only: bool = False
    client_order_id: str | None = None

    def normalized(self) -> "TestnetOrderRequest":
        symbol = self.symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol is required")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.order_type == OrderType.LIMIT and (self.price is None or self.price <= 0):
            raise ValueError("LIMIT order requires a positive price")
        if self.order_type == OrderType.MARKET and self.price is not None:
            raise ValueError("MARKET order cannot include price")
        return TestnetOrderRequest(
            symbol=symbol,
            side=self.side,
            order_type=self.order_type,
            quantity=float(self.quantity),
            price=None if self.price is None else float(self.price),
            reduce_only=bool(self.reduce_only),
            client_order_id=self.client_order_id,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["side"] = self.side.value
        data["order_type"] = self.order_type.value
        return data


@dataclass(frozen=True, slots=True)
class TestnetOrderResult:
    status: str
    idempotency_key: str
    client_order_id: str
    exchange_order_id: str | None
    request: TestnetOrderRequest
    duplicate: bool
    testnet: bool
    live_order_sent: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "idempotency_key": self.idempotency_key,
            "client_order_id": self.client_order_id,
            "exchange_order_id": self.exchange_order_id,
            "request": self.request.to_dict(),
            "duplicate": self.duplicate,
            "testnet": self.testnet,
            "live_order_sent": self.live_order_sent,
            "created_at": self.created_at.isoformat(),
        }
