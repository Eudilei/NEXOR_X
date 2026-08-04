from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from .engine import CQOCertificationEngine, CertificationPolicy
from .models import CertificationEvidence


class CertificationService:
    def __init__(
        self,
        database: Any,
        policy: CertificationPolicy | None = None,
    ) -> None:
        self.database = database
        self.engine = CQOCertificationEngine(policy)

    async def start(self) -> None:
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS cqo_certifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                passed INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    async def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        evidence = CertificationEvidence(
            paper_trades=int(payload["paper_trades"]),
            profit_factor=float(payload["profit_factor"]),
            expected_r=float(payload["expected_r"]),
            maximum_drawdown_pct=float(payload["maximum_drawdown_pct"]),
            walk_forward_pass_ratio=float(payload["walk_forward_pass_ratio"]),
            monte_carlo_ruin_probability=float(
                payload["monte_carlo_ruin_probability"]
            ),
            brier_score_oos=float(payload["brier_score_oos"]),
            calibration_ece_oos=float(payload["calibration_ece_oos"]),
            operational_incidents=int(payload["operational_incidents"]),
            critical_test_failures=int(payload["critical_test_failures"]),
            days_in_paper=int(payload["days_in_paper"]),
            recent_profit_factor=float(payload["recent_profit_factor"]),
            recent_expected_r=float(payload["recent_expected_r"]),
            data_freshness_ok=bool(payload["data_freshness_ok"]),
            reconciliation_ok=bool(payload["reconciliation_ok"]),
            secrets_configured=bool(payload["secrets_configured"]),
            live_connector_tested=bool(payload["live_connector_tested"]),
            manual_owner_approval=bool(payload.get("manual_owner_approval", False)),
        )
        result = self.engine.evaluate(evidence)
        data = result.to_dict()
        await self.database.execute(
            """
            INSERT INTO cqo_certifications(status, passed, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                result.status,
                1 if result.passed else 0,
                json.dumps(data, ensure_ascii=False),
                datetime.now(UTC).isoformat(),
            ),
        )
        return data

    async def status(self) -> dict[str, Any]:
        await self.start()
        rows = await self.database.fetchall(
            """
            SELECT payload_json
            FROM cqo_certifications
            ORDER BY id DESC
            LIMIT 1
            """
        )
        return {
            "state": "READY",
            "latest_certification": None if not rows else json.loads(str(rows[0][0])),
            "live_execution_allowed": False,
            "mode_switch_available": False,
        }
