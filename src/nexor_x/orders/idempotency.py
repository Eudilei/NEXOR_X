from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .models import TestnetOrderRequest


@dataclass(frozen=True, slots=True)
class OrderIntent:
    strategy_id: str
    signal_id: str
    request: TestnetOrderRequest

    def key(self) -> str:
        payload = {
            "strategy_id": self.strategy_id.strip(),
            "signal_id": self.signal_id.strip(),
            "request": self.request.normalized().to_dict(),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class IdempotencyRegistry:
    def __init__(self, database: Any) -> None:
        self.database = database

    async def start(self) -> None:
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS order_idempotency (
                idempotency_key TEXT PRIMARY KEY,
                client_order_id TEXT NOT NULL,
                exchange_order_id TEXT,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    async def get(self, key: str) -> dict[str, Any] | None:
        await self.start()
        rows = await self.database.fetchall(
            """
            SELECT client_order_id, exchange_order_id, status, payload_json, created_at
            FROM order_idempotency
            WHERE idempotency_key = ?
            LIMIT 1
            """,
            (key,),
        )
        if not rows:
            return None
        return {
            "client_order_id": str(rows[0][0]),
            "exchange_order_id": None if rows[0][1] is None else str(rows[0][1]),
            "status": str(rows[0][2]),
            "payload_json": str(rows[0][3]),
            "created_at": str(rows[0][4]),
        }

    async def reserve(
        self,
        *,
        key: str,
        client_order_id: str,
        payload_json: str,
        created_at: str,
    ) -> bool:
        await self.start()
        try:
            await self.database.execute(
                """
                INSERT INTO order_idempotency(
                    idempotency_key, client_order_id, exchange_order_id,
                    status, payload_json, created_at
                ) VALUES (?, ?, NULL, 'RESERVED', ?, ?)
                """,
                (key, client_order_id, payload_json, created_at),
            )
            return True
        except Exception:
            return False

    async def finalize(
        self,
        *,
        key: str,
        exchange_order_id: str | None,
        status: str,
    ) -> None:
        await self.database.execute(
            """
            UPDATE order_idempotency
            SET exchange_order_id = ?, status = ?
            WHERE idempotency_key = ?
            """,
            (exchange_order_id, status, key),
        )
