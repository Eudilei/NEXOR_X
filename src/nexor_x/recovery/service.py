from __future__ import annotations

from decimal import Decimal
import json
from typing import Any

from .models import RecoveryIssue, RecoveryReport


_TERMINAL_ORDER_STATUSES = {
    "CANCELED",
    "EXPIRED",
    "FILLED",
    "REJECTED",
}


def _side_from_exchange(position_amount: Decimal) -> str:
    return "LONG" if position_amount > 0 else "SHORT"


class RecoveryGuardService:
    """Detects state divergence after restarts and blocks new TESTNET orders.

    The service never mutates exchange or local position state. A human or a later
    supervised recovery workflow must resolve mismatches before the guard unlocks.
    """

    def __init__(self, database: Any, connector: Any) -> None:
        self.database = database
        self.connector = connector

    async def start(self) -> None:
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS recovery_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                recovery_ok INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    async def reconcile(self) -> dict[str, Any]:
        await self.start()
        if not getattr(self.connector.policy, "use_testnet", False):
            raise RuntimeError("Recovery reconciliation is restricted to TESTNET")

        local_positions = await self._local_positions()
        local_orders = await self._local_pending_orders()
        exchange_positions_raw = await self.connector.testnet_positions()
        exchange_orders_raw = await self.connector.testnet_open_orders()

        exchange_positions = self._normalize_exchange_positions(
            exchange_positions_raw
        )
        exchange_orders = self._normalize_exchange_orders(exchange_orders_raw)

        issues: list[RecoveryIssue] = []
        issues.extend(self._position_issues(local_positions, exchange_positions))
        issues.extend(self._order_issues(local_orders, exchange_orders))

        recovery_ok = not issues
        report = RecoveryReport(
            status="RECOVERED" if recovery_ok else "LOCKED",
            recovery_ok=recovery_ok,
            local_open_positions=len(local_positions),
            exchange_open_positions=len(exchange_positions),
            local_pending_orders=len(local_orders),
            exchange_open_orders=len(exchange_orders),
            issues=tuple(issues),
            testnet_order_guard_locked=not recovery_ok,
        )
        payload = report.to_dict()
        await self.database.execute(
            """
            INSERT INTO recovery_reports(
                status, recovery_ok, payload_json, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (
                report.status,
                1 if report.recovery_ok else 0,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                report.created_at.isoformat(),
            ),
        )
        return payload

    async def status(self) -> dict[str, Any]:
        await self.start()
        rows = await self.database.fetchall(
            """
            SELECT payload_json
            FROM recovery_reports
            ORDER BY id DESC
            LIMIT 1
            """
        )
        latest = None if not rows else json.loads(str(rows[0][0]))
        return {
            "state": "READY",
            "latest_report": latest,
            "testnet_order_guard_locked": (
                True if latest is None
                else bool(latest.get("testnet_order_guard_locked", True))
            ),
            "live_execution_allowed": False,
        }

    async def allows_testnet_orders(self) -> bool:
        status = await self.status()
        return not bool(status["testnet_order_guard_locked"])

    async def _local_positions(self) -> dict[tuple[str, str], Decimal]:
        rows = await self.database.fetchall(
            """
            SELECT symbol, side, quantity
            FROM portfolio_positions
            WHERE status = 'OPEN'
            """
        )
        result: dict[tuple[str, str], Decimal] = {}
        for symbol, side, quantity in rows:
            qty = Decimal(str(quantity))
            if qty == 0:
                continue
            result[(str(symbol).upper(), str(side).upper())] = qty
        return result

    async def _local_pending_orders(self) -> dict[str, dict[str, str]]:
        rows = await self.database.fetchall(
            """
            SELECT client_order_id, exchange_order_id, status, payload_json
            FROM order_idempotency
            WHERE status NOT IN ('CANCELED', 'EXPIRED', 'FILLED', 'REJECTED', 'FAILED')
            """
        )
        result: dict[str, dict[str, str]] = {}
        for client_id, exchange_id, status, payload_json in rows:
            result[str(client_id)] = {
                "client_order_id": str(client_id),
                "exchange_order_id": "" if exchange_id is None else str(exchange_id),
                "status": str(status),
                "payload_json": str(payload_json),
            }
        return result

    @staticmethod
    def _normalize_exchange_positions(
        rows: list[dict[str, Any]],
    ) -> dict[tuple[str, str], Decimal]:
        result: dict[tuple[str, str], Decimal] = {}
        for row in rows:
            amount = Decimal(str(row.get("positionAmt") or "0"))
            if amount == 0:
                continue
            symbol = str(row["symbol"]).upper()
            side = _side_from_exchange(amount)
            result[(symbol, side)] = abs(amount)
        return result

    @staticmethod
    def _normalize_exchange_orders(
        rows: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            client_id = str(row.get("clientOrderId") or "")
            if not client_id:
                continue
            status = str(row.get("status") or "UNKNOWN").upper()
            if status in _TERMINAL_ORDER_STATUSES:
                continue
            result[client_id] = row
        return result

    @staticmethod
    def _position_issues(
        local: dict[tuple[str, str], Decimal],
        exchange: dict[tuple[str, str], Decimal],
    ) -> list[RecoveryIssue]:
        issues: list[RecoveryIssue] = []
        keys = set(local) | set(exchange)
        for key in sorted(keys):
            symbol, side = key
            local_qty = local.get(key, Decimal("0"))
            exchange_qty = exchange.get(key, Decimal("0"))
            if local_qty == exchange_qty:
                continue
            if local_qty == 0:
                issue_type = "EXCHANGE_ONLY_POSITION"
            elif exchange_qty == 0:
                issue_type = "LOCAL_ONLY_POSITION"
            else:
                issue_type = "POSITION_QUANTITY_MISMATCH"
            issues.append(
                RecoveryIssue(
                    issue_type=issue_type,
                    symbol=symbol,
                    details=(
                        f"{side}: local={local_qty} exchange={exchange_qty}"
                    ),
                )
            )
        return issues

    @staticmethod
    def _order_issues(
        local: dict[str, dict[str, str]],
        exchange: dict[str, dict[str, Any]],
    ) -> list[RecoveryIssue]:
        issues: list[RecoveryIssue] = []
        keys = set(local) | set(exchange)
        for client_id in sorted(keys):
            local_item = local.get(client_id)
            exchange_item = exchange.get(client_id)
            if local_item is not None and exchange_item is not None:
                continue
            if local_item is None:
                symbol = str(exchange_item.get("symbol") or "UNKNOWN")
                issue_type = "EXCHANGE_ONLY_OPEN_ORDER"
                details = f"client_order_id={client_id}"
            else:
                payload = json.loads(local_item["payload_json"])
                symbol = str(
                    payload.get("request", {}).get("symbol") or "UNKNOWN"
                )
                issue_type = "LOCAL_ONLY_PENDING_ORDER"
                details = f"client_order_id={client_id}"
            issues.append(
                RecoveryIssue(
                    issue_type=issue_type,
                    symbol=symbol,
                    details=details,
                )
            )
        return issues
