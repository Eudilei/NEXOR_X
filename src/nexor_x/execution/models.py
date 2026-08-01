from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class PaperOrderStatus(StrEnum):
    FILLED = "FILLED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class PaperFill:
    position_id: int | None
    symbol: str
    side: str
    status: PaperOrderStatus
    quantity: float
    entry_price: float
    stop_price: float
    notional: float
    risk_budget: float
    fee_paid: float
    reason: str
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "side": self.side,
            "status": self.status.value,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "stop_price": self.stop_price,
            "notional": self.notional,
            "risk_budget": self.risk_budget,
            "fee_paid": self.fee_paid,
            "reason": self.reason,
            "created_at": self.created_at.astimezone(UTC).isoformat(),
            "live_order_sent": False,
        }
