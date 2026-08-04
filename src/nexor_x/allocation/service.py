from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from .engine import AdaptivePortfolioAllocator, AllocationPolicy
from .models import AllocationCandidate


class AllocationService:
    def __init__(
        self,
        database: Any,
        policy: AllocationPolicy | None = None,
    ) -> None:
        self.database = database
        self.allocator = AdaptivePortfolioAllocator(policy)

    async def start(self) -> None:
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS allocation_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    async def plan(
        self,
        *,
        portfolio_drawdown_pct: float,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        parsed = [
            AllocationCandidate(
                strategy_id=str(item["strategy_id"]),
                symbol=str(item["symbol"]).upper(),
                direction=str(item["direction"]).upper(),
                score=float(item["score"]),
                expected_r=float(item["expected_r"]),
                profit_factor=float(item["profit_factor"]),
                walk_forward_pass_ratio=float(item["walk_forward_pass_ratio"]),
                monte_carlo_ruin_probability=float(
                    item["monte_carlo_ruin_probability"]
                ),
                max_drawdown_r=float(item["max_drawdown_r"]),
                current_drawdown_pct=float(item.get("current_drawdown_pct", 0.0)),
                correlation_group=str(item.get("correlation_group", "DEFAULT")),
            )
            for item in candidates
        ]
        result = self.allocator.allocate(
            parsed,
            portfolio_drawdown_pct=float(portfolio_drawdown_pct),
        )
        payload = result.to_dict()
        await self.database.execute(
            """
            INSERT INTO allocation_plans(status, payload_json, created_at)
            VALUES (?, ?, ?)
            """,
            (
                result.status,
                json.dumps(payload, ensure_ascii=False),
                datetime.now(UTC).isoformat(),
            ),
        )
        return payload

    async def status(self) -> dict[str, Any]:
        await self.start()
        rows = await self.database.fetchall(
            """
            SELECT payload_json
            FROM allocation_plans
            ORDER BY id DESC
            LIMIT 1
            """
        )
        return {
            "state": "READY",
            "latest_plan": None if not rows else json.loads(str(rows[0][0])),
            "execution_allowed": False,
            "live_certified": False,
        }
