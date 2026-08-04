from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    symbol: str
    direction: str
    quantity: Decimal
    entry_price: Decimal

    def key(self) -> tuple[str, str]:
        return (self.symbol.upper(), self.direction.upper())


@dataclass(frozen=True, slots=True)
class ReconciliationIssue:
    issue_type: str
    symbol: str
    direction: str
    local_quantity: str
    exchange_quantity: str
    details: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    status: str
    matched_positions: int
    issues: tuple[ReconciliationIssue, ...]
    exchange_only_positions: int
    local_only_positions: int
    quantity_mismatches: int
    reconciliation_ok: bool
    execution_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "matched_positions": self.matched_positions,
            "issues": [item.to_dict() for item in self.issues],
            "exchange_only_positions": self.exchange_only_positions,
            "local_only_positions": self.local_only_positions,
            "quantity_mismatches": self.quantity_mismatches,
            "reconciliation_ok": self.reconciliation_ok,
            "execution_allowed": self.execution_allowed,
        }


class ReconciliationService:
    """Compares local and exchange position snapshots without modifying either side."""

    def __init__(self, quantity_tolerance: Decimal = Decimal("0.00000001")) -> None:
        self.quantity_tolerance = quantity_tolerance

    def reconcile(
        self,
        local_positions: Iterable[PositionSnapshot],
        exchange_positions: Iterable[PositionSnapshot],
    ) -> ReconciliationReport:
        local = {item.key(): item for item in local_positions if item.quantity != 0}
        exchange = {item.key(): item for item in exchange_positions if item.quantity != 0}

        issues: list[ReconciliationIssue] = []
        matched = 0
        exchange_only = 0
        local_only = 0
        mismatches = 0

        for key in sorted(set(local) | set(exchange)):
            local_item = local.get(key)
            exchange_item = exchange.get(key)
            symbol, direction = key

            if local_item is None and exchange_item is not None:
                exchange_only += 1
                issues.append(
                    ReconciliationIssue(
                        issue_type="EXCHANGE_ONLY_POSITION",
                        symbol=symbol,
                        direction=direction,
                        local_quantity="0",
                        exchange_quantity=str(exchange_item.quantity),
                        details="Position exists on exchange but not in local ledger.",
                    )
                )
                continue

            if exchange_item is None and local_item is not None:
                local_only += 1
                issues.append(
                    ReconciliationIssue(
                        issue_type="LOCAL_ONLY_POSITION",
                        symbol=symbol,
                        direction=direction,
                        local_quantity=str(local_item.quantity),
                        exchange_quantity="0",
                        details="Position exists locally but not on exchange.",
                    )
                )
                continue

            assert local_item is not None and exchange_item is not None
            difference = abs(local_item.quantity - exchange_item.quantity)
            if difference > self.quantity_tolerance:
                mismatches += 1
                issues.append(
                    ReconciliationIssue(
                        issue_type="QUANTITY_MISMATCH",
                        symbol=symbol,
                        direction=direction,
                        local_quantity=str(local_item.quantity),
                        exchange_quantity=str(exchange_item.quantity),
                        details=f"Quantity difference {difference} exceeds tolerance.",
                    )
                )
            else:
                matched += 1

        ok = not issues
        return ReconciliationReport(
            status="MATCHED" if ok else "MISMATCH",
            matched_positions=matched,
            issues=tuple(issues),
            exchange_only_positions=exchange_only,
            local_only_positions=local_only,
            quantity_mismatches=mismatches,
            reconciliation_ok=ok,
            execution_allowed=False,
        )
