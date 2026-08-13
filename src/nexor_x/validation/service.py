from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from .engine import ValidationSnapshotEngine, ValidationSnapshotInput


class ValidationSnapshotService:
    def __init__(self, database: Any) -> None:
        self.database = database
        self.engine = ValidationSnapshotEngine()

    async def start(self) -> None:
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                paper_ready INTEGER NOT NULL,
                testnet_ready INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    async def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        inputs = ValidationSnapshotInput(
            paper_trades=int(payload["paper_trades"]),
            profit_factor=float(payload["profit_factor"]),
            expected_r=float(payload["expected_r"]),
            drawdown_pct=float(payload["drawdown_pct"]),
            recent_profit_factor=float(payload["recent_profit_factor"]),
            recent_expected_r=float(payload["recent_expected_r"]),
            walk_forward_pass_ratio=float(payload["walk_forward_pass_ratio"]),
            monte_carlo_ruin_probability=float(
                payload["monte_carlo_ruin_probability"]
            ),
            brier_score_oos=float(payload["brier_score_oos"]),
            calibration_ece_oos=float(payload["calibration_ece_oos"]),
            integration_healthy=bool(payload["integration_healthy"]),
            recovery_ok=bool(payload["recovery_ok"]),
            supervisor_paper_allowed=bool(
                payload["supervisor_paper_allowed"]
            ),
            supervisor_testnet_allowed=bool(
                payload["supervisor_testnet_allowed"]
            ),
            operational_incidents=int(payload["operational_incidents"]),
            critical_test_failures=int(payload["critical_test_failures"]),
        )
        report = self.engine.evaluate(inputs)
        result = report.to_dict()
        await self.database.execute(
            """
            INSERT INTO validation_snapshots(
                status, paper_ready, testnet_ready, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                report.status,
                1 if report.paper_validation_ready else 0,
                1 if report.testnet_validation_ready else 0,
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
            FROM validation_snapshots
            ORDER BY id DESC
            LIMIT 1
            """
        )
        latest = None if not rows else json.loads(str(rows[0][0]))
        return {
            "state": "READY",
            "latest": latest,
            "live_validation_ready": False,
        }
