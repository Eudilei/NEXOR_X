from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from .models import (
    StrategyDefinition,
    StrategyMetric,
    StrategySelection,
    StrategyStatus,
)


class StrategyRepository:
    """Persistence adapter compatible with the existing DatabaseService API."""

    def __init__(self, database: Any) -> None:
        self.database = database

    async def ensure_schema(self) -> None:
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS strategy_registry (
                strategy_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                status TEXT NOT NULL,
                supported_regimes_json TEXT NOT NULL,
                supported_directions_json TEXT NOT NULL,
                description TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS strategy_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT NOT NULL,
                regime TEXT NOT NULL,
                decision TEXT NOT NULL,
                sample_count INTEGER NOT NULL,
                profit_factor REAL NOT NULL,
                expected_r REAL NOT NULL,
                win_rate REAL NOT NULL,
                max_drawdown_r REAL NOT NULL,
                brier_score REAL,
                walk_forward_pass_ratio REAL,
                monte_carlo_ruin_probability REAL,
                updated_at TEXT NOT NULL
            )
            """
        )
        await self.database.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_strategy_metrics_context
            ON strategy_metrics(strategy_id, regime, decision, updated_at DESC)
            """
        )
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS strategy_selections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                regime TEXT NOT NULL,
                decision TEXT NOT NULL,
                selected_strategy_id TEXT,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await self.database.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_strategy_selections_created
            ON strategy_selections(created_at DESC)
            """
        )

    async def upsert_definition(self, definition: StrategyDefinition) -> None:
        await self.ensure_schema()
        await self.database.execute(
            """
            INSERT INTO strategy_registry (
                strategy_id, name, version, status, supported_regimes_json,
                supported_directions_json, description, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(strategy_id) DO UPDATE SET
                name=excluded.name,
                version=excluded.version,
                status=excluded.status,
                supported_regimes_json=excluded.supported_regimes_json,
                supported_directions_json=excluded.supported_directions_json,
                description=excluded.description,
                updated_at=excluded.updated_at
            """,
            (
                definition.strategy_id,
                definition.name,
                definition.version,
                definition.status.value,
                json.dumps(definition.supported_regimes),
                json.dumps(definition.supported_directions),
                definition.description,
                datetime.now(UTC).isoformat(),
            ),
        )

    async def list_definitions(self) -> list[StrategyDefinition]:
        await self.ensure_schema()
        rows = await self.database.fetchall(
            """
            SELECT strategy_id, name, supported_regimes_json,
                   supported_directions_json, status, version, description
            FROM strategy_registry
            ORDER BY strategy_id
            """
        )
        return [
            StrategyDefinition(
                strategy_id=str(row[0]),
                name=str(row[1]),
                supported_regimes=tuple(json.loads(str(row[2]))),
                supported_directions=tuple(json.loads(str(row[3]))),
                status=StrategyStatus(str(row[4])),
                version=str(row[5]),
                description=str(row[6]),
            )
            for row in rows
        ]

    async def save_metric(self, metric: StrategyMetric) -> None:
        await self.ensure_schema()
        await self.database.execute(
            """
            INSERT INTO strategy_metrics (
                strategy_id, regime, decision, sample_count, profit_factor,
                expected_r, win_rate, max_drawdown_r, brier_score,
                walk_forward_pass_ratio, monte_carlo_ruin_probability, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metric.strategy_id,
                metric.regime,
                metric.decision,
                metric.sample_count,
                metric.profit_factor,
                metric.expected_r,
                metric.win_rate,
                metric.max_drawdown_r,
                metric.brier_score,
                metric.walk_forward_pass_ratio,
                metric.monte_carlo_ruin_probability,
                metric.updated_at.isoformat(),
            ),
        )

    async def save_selection(self, selection: StrategySelection) -> None:
        await self.ensure_schema()
        await self.database.execute(
            """
            INSERT INTO strategy_selections (
                symbol, regime, decision, selected_strategy_id, status,
                payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                selection.symbol,
                selection.regime,
                selection.decision,
                selection.selected_strategy_id,
                selection.status,
                json.dumps(selection.to_dict(), ensure_ascii=False),
                selection.created_at.isoformat(),
            ),
        )

    async def latest_selection(self) -> dict[str, Any] | None:
        await self.ensure_schema()
        rows = await self.database.fetchall(
            """
            SELECT payload_json
            FROM strategy_selections
            ORDER BY id DESC
            LIMIT 1
            """
        )
        if not rows:
            return None
        return dict(json.loads(str(rows[0][0])))
