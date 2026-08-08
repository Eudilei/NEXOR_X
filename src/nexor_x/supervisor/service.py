from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from .engine import OperationalSupervisor, SupervisorInputs


class OperationalSupervisorService:
    def __init__(self, database: Any) -> None:
        self.database = database
        self.engine = OperationalSupervisor()

    async def start(self) -> None:
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS operational_supervisor_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                paper_allowed INTEGER NOT NULL,
                testnet_allowed INTEGER NOT NULL,
                live_allowed INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    async def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        inputs = SupervisorInputs(
            mode=str(payload.get("mode", "PAPER")),
            recovery_ok=bool(payload.get("recovery_ok", False)),
            exchange_ready=bool(payload.get("exchange_ready", False)),
            certification_passed=bool(
                payload.get("certification_passed", False)
            ),
            live_connector_tested=bool(
                payload.get("live_connector_tested", False)
            ),
            data_freshness_ok=bool(payload.get("data_freshness_ok", False)),
            hard_stop_active=bool(payload.get("hard_stop_active", False)),
            critical_test_failures=int(
                payload.get("critical_test_failures", 0)
            ),
            operational_incidents=int(
                payload.get("operational_incidents", 0)
            ),
        )
        decision = self.engine.evaluate(inputs)
        result = decision.to_dict()
        await self.database.execute(
            """
            INSERT INTO operational_supervisor_reports(
                status, paper_allowed, testnet_allowed, live_allowed,
                payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                decision.status,
                1 if decision.paper_allowed else 0,
                1 if decision.testnet_allowed else 0,
                1 if decision.live_allowed else 0,
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
            FROM operational_supervisor_reports
            ORDER BY id DESC
            LIMIT 1
            """
        )
        latest = None if not rows else json.loads(str(rows[0][0]))
        return {
            "state": "READY",
            "latest": latest,
            "live_allowed": False,
        }
