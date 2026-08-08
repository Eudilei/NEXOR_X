from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any


class OrderAuditRepository:
    def __init__(self, database: Any) -> None:
        self.database = database

    async def start(self) -> None:
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS order_audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                client_order_id TEXT,
                exchange_order_id TEXT,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    async def save(
        self,
        *,
        event_type: str,
        symbol: str,
        payload: dict[str, Any],
        client_order_id: str | None = None,
        exchange_order_id: str | None = None,
    ) -> None:
        await self.start()
        await self.database.execute(
            """
            INSERT INTO order_audit_events(
                event_type, symbol, client_order_id, exchange_order_id,
                payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                symbol.upper(),
                client_order_id,
                exchange_order_id,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                datetime.now(UTC).isoformat(),
            ),
        )

    async def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        await self.start()
        rows = await self.database.fetchall(
            """
            SELECT event_type, symbol, client_order_id, exchange_order_id,
                   payload_json, created_at
            FROM order_audit_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        return [
            {
                "event_type": str(row[0]),
                "symbol": str(row[1]),
                "client_order_id": None if row[2] is None else str(row[2]),
                "exchange_order_id": None if row[3] is None else str(row[3]),
                "payload": json.loads(str(row[4])),
                "created_at": str(row[5]),
            }
            for row in rows
        ]
