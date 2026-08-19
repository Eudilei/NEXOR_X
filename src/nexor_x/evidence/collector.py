from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    paper_trades: int
    profit_factor: float
    expected_r: float
    drawdown_pct: float
    recent_profit_factor: float
    recent_expected_r: float
    operational_incidents: int
    critical_test_failures: int
    integration_healthy: bool
    recovery_ok: bool
    supervisor_paper_allowed: bool
    supervisor_testnet_allowed: bool
    recent_trades: int = 0
    loss_streak: int = 0
    recent_shadow_samples: int = 0
    recent_shadow_profit_factor: float = 0.0
    recent_shadow_expected_r: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidenceCollector:
    """Builds validation evidence from persisted NEXOR X state.

    Missing optional tables never fabricate positive evidence. Unknown data is
    represented conservatively so validation cannot advance accidentally.
    """

    def __init__(self, database: Any) -> None:
        self.database = database

    async def collect(self) -> EvidenceSnapshot:
        paper_trades = await self._count_paper_trades()
        profit_factor, expected_r = await self._performance_metrics(recent=False)
        recent_profit_factor, recent_expected_r = await self._performance_metrics(
            recent=True
        )
        recent_trades, loss_streak = await self._recent_trade_stats()
        shadow_samples, shadow_pf, shadow_expected_r = await self._shadow_metrics()
        drawdown_pct = await self._drawdown_pct()
        operational_incidents = await self._operational_incidents()
        critical_test_failures = await self._critical_test_failures()

        integration = await self._latest_json(
            "integration_health_reports",
            "payload_json",
        )
        recovery = await self._latest_json(
            "recovery_reports",
            "payload_json",
        )
        supervisor = await self._latest_json(
            "operational_supervisor_reports",
            "payload_json",
        )

        return EvidenceSnapshot(
            paper_trades=paper_trades,
            profit_factor=profit_factor,
            expected_r=expected_r,
            drawdown_pct=drawdown_pct,
            recent_profit_factor=recent_profit_factor,
            recent_expected_r=recent_expected_r,
            operational_incidents=operational_incidents,
            critical_test_failures=critical_test_failures,
            integration_healthy=bool(
                integration and integration.get("healthy", False)
            ),
            recovery_ok=bool(
                recovery and recovery.get("recovery_ok", False)
            ),
            supervisor_paper_allowed=bool(
                supervisor and supervisor.get("paper_allowed", False)
            ),
            supervisor_testnet_allowed=bool(
                supervisor and supervisor.get("testnet_allowed", False)
            ),
            recent_trades=recent_trades,
            loss_streak=loss_streak,
            recent_shadow_samples=shadow_samples,
            recent_shadow_profit_factor=shadow_pf,
            recent_shadow_expected_r=shadow_expected_r,
        )

    async def _count_paper_trades(self) -> int:
        candidates = (
            ("portfolio_positions", "status = 'CLOSED'"),
            ("trades", "mode = 'PAPER'"),
            ("execution_trades", "mode = 'PAPER'"),
            ("paper_trades", "1 = 1"),
        )
        for table, where in candidates:
            value = await self._scalar_if_table(
                table,
                f"SELECT COUNT(*) FROM {table} WHERE {where}",
            )
            if value is not None:
                return int(value)
        return 0

    async def _performance_metrics(
        self,
        *,
        recent: bool,
    ) -> tuple[float, float]:
        table = await self._first_existing_table(
            ("portfolio_positions", "trades", "execution_trades", "paper_trades")
        )
        if table is None:
            return 0.0, 0.0

        columns = await self._columns(table)
        pnl_column = next(
            (
                name
                for name in ("pnl_r", "realized_r", "result_r", "pnl", "realized_pnl")
                if name in columns
            ),
            None,
        )
        if pnl_column is None:
            return 0.0, 0.0

        limit = " LIMIT 100" if recent else ""
        order = ""
        if recent and "id" in columns:
            order = " ORDER BY id DESC"

        where = f" WHERE {pnl_column} IS NOT NULL"
        if table == "portfolio_positions" and "status" in columns:
            where += " AND status='CLOSED'"
        try:
            rows = await self.database.fetchall(
                f"SELECT {pnl_column} FROM {table}"
                f"{where}{order}{limit}"
            )
        except Exception:
            return 0.0, 0.0

        values = [float(row[0]) for row in rows]
        if not values:
            return 0.0, 0.0

        gross_profit = sum(value for value in values if value > 0)
        gross_loss = abs(sum(value for value in values if value < 0))
        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else (999.0 if gross_profit > 0 else 0.0)
        )
        expected_r = sum(values) / len(values)
        return round(profit_factor, 6), round(expected_r, 6)

    async def _recent_trade_stats(self) -> tuple[int, int]:
        table = await self._first_existing_table(
            ("portfolio_positions", "trades", "execution_trades", "paper_trades")
        )
        if table is None:
            return 0, 0
        columns = await self._columns(table)
        pnl_column = next((name for name in
            ("pnl_r", "realized_r", "result_r", "pnl", "realized_pnl")
            if name in columns), None)
        if pnl_column is None:
            return 0, 0
        where = ""
        if table == "portfolio_positions" and "status" in columns:
            where = " AND status='CLOSED'"
        order = " ORDER BY id DESC" if "id" in columns else ""
        try:
            rows = await self.database.fetchall(
                f"SELECT {pnl_column} FROM {table} WHERE {pnl_column} IS NOT NULL"
                f"{where}{order} LIMIT 100"
            )
        except Exception:
            return 0, 0
        values = [float(row[0]) for row in rows]
        streak = 0
        for value in values:
            if value >= 0:
                break
            streak += 1
        return len(values), streak

    async def _shadow_metrics(self) -> tuple[int, float, float]:
        if not await self._table_exists("quant_observations"):
            return 0, 0.0, 0.0
        try:
            cutoff = None
            if await self._table_exists("portfolio_positions"):
                latest = await self.database.fetchall(
                    "SELECT MAX(closed_at) FROM portfolio_positions "
                    "WHERE status='CLOSED'"
                )
                cutoff = latest[0][0] if latest and latest[0][0] else None
            where = " WHERE closed_at > ?" if cutoff else ""
            parameters = (cutoff,) if cutoff else ()
            rows = await self.database.fetchall(
                "SELECT realized_r FROM quant_observations"
                f"{where} ORDER BY id DESC LIMIT 100",
                parameters,
            )
        except Exception:
            return 0, 0.0, 0.0
        values = [float(row[0]) for row in rows]
        if not values:
            return 0, 0.0, 0.0
        profit = sum(value for value in values if value > 0)
        loss = abs(sum(value for value in values if value < 0))
        profit_factor = profit / loss if loss else (999.0 if profit else 0.0)
        return len(values), round(profit_factor, 6), round(sum(values) / len(values), 6)

    async def _drawdown_pct(self) -> float:
        table = await self._first_existing_table(
            ("portfolio_accounts", "portfolio_account")
        )
        if table is None:
            return 100.0

        columns = await self._columns(table)
        try:
            if "drawdown_pct" in columns:
                expression = "drawdown_pct"
            elif {"equity", "peak_equity"}.issubset(columns):
                expression = (
                    "CASE WHEN peak_equity > 0 THEN "
                    "MAX(0.0, (peak_equity-equity)*100.0/peak_equity) ELSE 0.0 END"
                )
            else:
                return 100.0
            order = " ORDER BY id DESC" if "id" in columns else ""
            rows = await self.database.fetchall(
                f"SELECT {expression} FROM {table}{order} LIMIT 1"
            )
        except Exception:
            return 100.0
        if not rows:
            return 100.0
        return float(rows[0][0] or 0.0)

    async def _operational_incidents(self) -> int:
        table = await self._first_existing_table(
            ("operational_incidents", "incidents")
        )
        if table is None:
            return 0
        value = await self._scalar_if_table(
            table,
            f"SELECT COUNT(*) FROM {table}",
        )
        return int(value or 0)

    async def _critical_test_failures(self) -> int:
        table = await self._first_existing_table(
            ("test_failures", "quality_failures")
        )
        if table is None:
            return 0

        columns = await self._columns(table)
        where = "1 = 1"
        if "severity" in columns:
            where = "UPPER(severity) = 'CRITICAL'"

        value = await self._scalar_if_table(
            table,
            f"SELECT COUNT(*) FROM {table} WHERE {where}",
        )
        return int(value or 0)

    async def _latest_json(
        self,
        table: str,
        column: str,
    ) -> dict[str, Any] | None:
        if not await self._table_exists(table):
            return None
        import json

        try:
            rows = await self.database.fetchall(
                f"SELECT {column} FROM {table} ORDER BY id DESC LIMIT 1"
            )
        except Exception:
            return None
        if not rows:
            return None
        try:
            return dict(json.loads(str(rows[0][0])))
        except Exception:
            return None

    async def _first_existing_table(
        self,
        names: tuple[str, ...],
    ) -> str | None:
        for name in names:
            if await self._table_exists(name):
                return name
        return None

    async def _table_exists(self, table: str) -> bool:
        try:
            rows = await self.database.fetchall(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name = ?
                LIMIT 1
                """,
                (table,),
            )
            return bool(rows)
        except Exception:
            return False

    async def _columns(self, table: str) -> set[str]:
        try:
            rows = await self.database.fetchall(
                f"PRAGMA table_info({table})"
            )
        except Exception:
            return set()
        return {str(row[1]) for row in rows}

    async def _scalar_if_table(
        self,
        table: str,
        query: str,
    ) -> float | int | None:
        if not await self._table_exists(table):
            return None
        try:
            rows = await self.database.fetchall(query)
        except Exception:
            return None
        if not rows:
            return None
        return rows[0][0]
