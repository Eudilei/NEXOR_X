from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from .engine import ContextBacktestEngine, ContextBacktestPolicy


class ContextBacktestService:
    """Runs and persists the fast contextual backtest before an entry."""

    def __init__(
        self,
        database: Any,
        laboratory: Any,
        policy: ContextBacktestPolicy | None = None,
    ) -> None:
        self.database = database
        self.laboratory = laboratory
        self.engine = ContextBacktestEngine(policy)

    async def start(self) -> None:
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS pretrade_context_backtests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                decision TEXT NOT NULL,
                regime TEXT NOT NULL,
                status TEXT NOT NULL,
                approved INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    async def evaluate(
        self,
        *,
        symbol: str,
        decision: str,
        regime: str,
    ) -> dict[str, Any]:
        await self.start()
        observations = await self.laboratory.observations()
        matching = [
            observation
            for observation in observations
            if observation.symbol.upper() == symbol.upper()
            and observation.decision.upper() == decision.upper()
            and observation.regime.upper() == regime.upper()
        ]
        matching.sort(key=lambda item: item.closed_at)

        report = self.engine.evaluate(
            symbol=symbol,
            decision=decision,
            regime=regime,
            realized_r=[item.realized_r for item in matching],
        )
        payload = report.to_dict()
        created_at = datetime.now(UTC).isoformat()

        await self.database.execute(
            """
            INSERT INTO pretrade_context_backtests(
                symbol, decision, regime, status, approved,
                payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.symbol,
                report.decision,
                report.regime,
                report.status,
                1 if report.approved else 0,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                created_at,
            ),
        )
        return payload

    async def latest(
        self,
        *,
        symbol: str | None = None,
    ) -> dict[str, Any]:
        await self.start()
        if symbol:
            rows = await self.database.fetchall(
                """
                SELECT payload_json, created_at
                FROM pretrade_context_backtests
                WHERE symbol = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (symbol.upper(),),
            )
        else:
            rows = await self.database.fetchall(
                """
                SELECT payload_json, created_at
                FROM pretrade_context_backtests
                ORDER BY id DESC
                LIMIT 1
                """
            )

        if not rows:
            return {
                "state": "READY",
                "latest": None,
                "execution_allowed": False,
                "live_execution_allowed": False,
            }

        return {
            "state": "READY",
            "latest": json.loads(str(rows[0][0])),
            "created_at": str(rows[0][1]),
            "execution_allowed": False,
            "live_execution_allowed": False,
        }
