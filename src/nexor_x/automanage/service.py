from __future__ import annotations
from datetime import UTC, datetime
import json
from typing import Any

class AutoPositionManagementService:
    def __init__(self, database: Any, manage_all_positions: Any) -> None:
        self.database = database
        self.manage_all_positions = manage_all_positions

    async def start(self) -> None:
        await self.database.execute("""
            CREATE TABLE IF NOT EXISTS auto_position_management_cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluated_positions INTEGER NOT NULL,
                action_count INTEGER NOT NULL,
                closed_positions INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

    async def run_once(self) -> dict[str, Any]:
        await self.start()
        result = await self.manage_all_positions()
        positions = list(result.get("positions") or [])
        action_count = sum(len(list(p.get("actions") or [])) for p in positions if isinstance(p, dict))
        closed_positions = sum(1 for p in positions if isinstance(p, dict) and bool(p.get("closed")))
        created_at = datetime.now(UTC).isoformat()
        payload = {
            "status": "OK",
            "evaluated_positions": int(result.get("evaluated") or 0),
            "skipped": list(result.get("skipped") or []),
            "action_count": action_count,
            "closed_positions": closed_positions,
            "positions": positions,
            "created_at": created_at,
            "live_execution_allowed": False,
        }
        await self.database.execute("""
            INSERT INTO auto_position_management_cycles(
                evaluated_positions, action_count, closed_positions,
                payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (payload["evaluated_positions"], action_count, closed_positions,
              json.dumps(payload, ensure_ascii=False, sort_keys=True), created_at))
        return payload

    async def status(self) -> dict[str, Any]:
        await self.start()
        rows = await self.database.fetchall("""
            SELECT payload_json FROM auto_position_management_cycles
            ORDER BY id DESC LIMIT 1
        """)
        latest = None if not rows else json.loads(str(rows[0][0]))
        return {"state": "READY", "latest": latest, "live_execution_allowed": False}
