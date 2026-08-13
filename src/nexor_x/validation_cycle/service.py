from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any


class ValidationCycleService:
    """Runs the validation campaign using evidence collected from persisted state.

    The cycle never opens orders and never changes the operating mode.
    """

    def __init__(
        self,
        database: Any,
        evidence_collector: Any,
        validation_campaign: Any,
    ) -> None:
        self.database = database
        self.evidence_collector = evidence_collector
        self.validation_campaign = validation_campaign

    async def start(self) -> None:
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_cycle_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                started_at TEXT NOT NULL
            )
            """
        )
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_cycle_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                days_running INTEGER NOT NULL,
                evidence_json TEXT NOT NULL,
                campaign_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        rows = await self.database.fetchall(
            "SELECT started_at FROM validation_cycle_state WHERE id = 1"
        )
        if not rows:
            await self.database.execute(
                """
                INSERT INTO validation_cycle_state(id, started_at)
                VALUES (1, ?)
                """,
                (datetime.now(UTC).isoformat(),),
            )

    async def run_once(self) -> dict[str, Any]:
        await self.start()
        evidence = await self.evidence_collector.collect()
        evidence_payload = evidence.to_dict()
        days_running = await self._days_running()

        campaign_payload = {
            "days_running": days_running,
            **evidence_payload,
        }
        campaign = await self.validation_campaign.evaluate(campaign_payload)

        created_at = datetime.now(UTC).isoformat()
        await self.database.execute(
            """
            INSERT INTO validation_cycle_runs(
                days_running, evidence_json, campaign_json, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (
                days_running,
                json.dumps(
                    evidence_payload,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                json.dumps(
                    campaign,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                created_at,
            ),
        )

        return {
            "status": "OK",
            "days_running": days_running,
            "evidence": evidence_payload,
            "campaign": campaign,
            "live_allowed": False,
            "created_at": created_at,
        }

    async def status(self) -> dict[str, Any]:
        await self.start()
        rows = await self.database.fetchall(
            """
            SELECT days_running, evidence_json, campaign_json, created_at
            FROM validation_cycle_runs
            ORDER BY id DESC
            LIMIT 1
            """
        )
        latest = None
        if rows:
            latest = {
                "days_running": int(rows[0][0]),
                "evidence": json.loads(str(rows[0][1])),
                "campaign": json.loads(str(rows[0][2])),
                "created_at": str(rows[0][3]),
                "live_allowed": False,
            }

        return {
            "state": "READY",
            "latest": latest,
            "live_allowed": False,
        }

    async def _days_running(self) -> int:
        rows = await self.database.fetchall(
            "SELECT started_at FROM validation_cycle_state WHERE id = 1"
        )
        if not rows:
            return 0
        started_at = datetime.fromisoformat(str(rows[0][0]))
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        elapsed = datetime.now(UTC) - started_at.astimezone(UTC)
        return max(int(elapsed.total_seconds() // 86400), 0)
