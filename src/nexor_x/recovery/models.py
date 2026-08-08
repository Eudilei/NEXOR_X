from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class RecoveryIssue:
    issue_type: str
    symbol: str
    details: str
    severity: str = "CRITICAL"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    status: str
    recovery_ok: bool
    local_open_positions: int
    exchange_open_positions: int
    local_pending_orders: int
    exchange_open_orders: int
    issues: tuple[RecoveryIssue, ...]
    testnet_order_guard_locked: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "recovery_ok": self.recovery_ok,
            "local_open_positions": self.local_open_positions,
            "exchange_open_positions": self.exchange_open_positions,
            "local_pending_orders": self.local_pending_orders,
            "exchange_open_orders": self.exchange_open_orders,
            "issues": [item.to_dict() for item in self.issues],
            "testnet_order_guard_locked": self.testnet_order_guard_locked,
            "created_at": self.created_at.isoformat(),
        }
