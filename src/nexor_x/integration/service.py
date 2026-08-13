from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from .engine import IntegrationHealthEngine, IntegrationHealthInput


class IntegrationHealthService:
    def __init__(self, database: Any) -> None:
        self.database = database
        self.engine = IntegrationHealthEngine()

    async def start(self) -> None:
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS integration_health_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                healthy INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    async def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        inputs = IntegrationHealthInput(
            database_ok=bool(payload.get("database_ok", False)),
            market_ok=bool(payload.get("market_ok", False)),
            scanner_ok=bool(payload.get("scanner_ok", False)),
            strategy_ok=bool(payload.get("strategy_ok", False)),
            allocation_ok=bool(payload.get("allocation_ok", False)),
            recovery_ok=bool(payload.get("recovery_ok", False)),
            supervisor_ok=bool(payload.get("supervisor_ok", False)),
            certification_ok=bool(payload.get("certification_ok", False)),
            update_registry_ok=bool(payload.get("update_registry_ok", False)),
            testnet_connector_ok=bool(
                payload.get("testnet_connector_ok", False)
            ),
            critical_test_failures=int(
                payload.get("critical_test_failures", 0)
            ),
            operational_incidents=int(
                payload.get("operational_incidents", 0)
            ),
        )

        report = self.engine.evaluate(inputs)
        result = report.to_dict()
        await self.database.execute(
            """
            INSERT INTO integration_health_reports(
                status, healthy, payload_json, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (
                report.status,
                1 if report.healthy else 0,
                json.dumps(result, ensure_ascii=False, sort_keys=True),
                datetime.now(UTC).isoformat(),
            ),
        )
        return result

    async def status(self) -> dict[str, Any]:
        await self.start()
        rows = await self.database.fetchall(
            """
            SELECT payload_json
            FROM integration_health_reports
            ORDER BY id DESC
            LIMIT 1
            """
        )
        latest = None if not rows else json.loads(str(rows[0][0]))
        return {
            "state": "READY",
            "latest": latest,
            "live_ready": False,
        }
