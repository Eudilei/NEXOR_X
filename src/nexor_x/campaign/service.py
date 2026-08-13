from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from .engine import ValidationCampaignEngine, ValidationCampaignInput


class ValidationCampaignService:
    def __init__(self, database: Any) -> None:
        self.database = database
        self.engine = ValidationCampaignEngine()

    async def start(self) -> None:
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_campaign_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phase TEXT NOT NULL,
                continue_campaign INTEGER NOT NULL,
                paper_allowed INTEGER NOT NULL,
                testnet_allowed INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    async def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        inputs = ValidationCampaignInput(
            days_running=int(payload["days_running"]),
            paper_trades=int(payload["paper_trades"]),
            profit_factor=float(payload["profit_factor"]),
            expected_r=float(payload["expected_r"]),
            drawdown_pct=float(payload["drawdown_pct"]),
            recent_profit_factor=float(payload["recent_profit_factor"]),
            recent_expected_r=float(payload["recent_expected_r"]),
            operational_incidents=int(payload["operational_incidents"]),
            critical_test_failures=int(payload["critical_test_failures"]),
            integration_healthy=bool(payload["integration_healthy"]),
            recovery_ok=bool(payload["recovery_ok"]),
            supervisor_paper_allowed=bool(
                payload["supervisor_paper_allowed"]
            ),
            supervisor_testnet_allowed=bool(
                payload["supervisor_testnet_allowed"]
            ),
        )
        report = self.engine.evaluate(inputs)
        result = report.to_dict()
        await self.database.execute(
            """
            INSERT INTO validation_campaign_reports(
                phase, continue_campaign, paper_allowed, testnet_allowed,
                payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                report.phase,
                1 if report.continue_campaign else 0,
                1 if report.paper_allowed else 0,
                1 if report.testnet_allowed else 0,
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
            FROM validation_campaign_reports
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
