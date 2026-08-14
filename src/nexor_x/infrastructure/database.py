from __future__ import annotations
import asyncio
import sqlite3
from pathlib import Path
from nexor_x.core.service import BaseService
from nexor_x.domain import ServiceState

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS system_events(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 event_id TEXT NOT NULL UNIQUE,
 topic TEXT NOT NULL,
 source TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 occurred_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS certifications(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 status TEXT NOT NULL,
 issued_at TEXT NOT NULL,
 evidence_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings_audit(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 key TEXT NOT NULL,
 old_value TEXT,
 new_value TEXT,
 actor TEXT NOT NULL,
 changed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quant_observations(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 symbol TEXT NOT NULL,
 decision TEXT NOT NULL,
 raw_edge REAL NOT NULL CHECK(raw_edge >= -1.0 AND raw_edge <= 1.0),
 regime TEXT NOT NULL,
 realized_r REAL NOT NULL,
 closed_at TEXT NOT NULL,
 UNIQUE(symbol, decision, raw_edge, regime, closed_at)
);
CREATE INDEX IF NOT EXISTS idx_quant_observations_context
ON quant_observations(decision, regime, raw_edge, closed_at);

CREATE TABLE IF NOT EXISTS portfolio_accounts(
 account_id TEXT PRIMARY KEY,
 equity REAL NOT NULL,
 peak_equity REAL NOT NULL,
 realized_pnl REAL NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS portfolio_positions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 symbol TEXT NOT NULL,
 side TEXT NOT NULL,
 quantity REAL NOT NULL,
 entry_price REAL NOT NULL,
 notional REAL NOT NULL,
 status TEXT NOT NULL,
 opened_at TEXT NOT NULL,
 closed_at TEXT,
 stop_price REAL,
 entry_fee REAL NOT NULL DEFAULT 0.0,
 exit_price REAL,
 exit_fee REAL NOT NULL DEFAULT 0.0,
 gross_pnl REAL NOT NULL DEFAULT 0.0,
 total_fees REAL NOT NULL DEFAULT 0.0,
 realized_pnl REAL NOT NULL DEFAULT 0.0,
 pnl_basis TEXT NOT NULL DEFAULT 'NET_AFTER_FEES',
 close_reason TEXT,
 initial_stop_price REAL,
 highest_price REAL,
 lowest_price REAL,
 partial_taken INTEGER NOT NULL DEFAULT 0,
 partial_realized_pnl REAL NOT NULL DEFAULT 0.0
);
CREATE INDEX IF NOT EXISTS idx_portfolio_positions_status
ON portfolio_positions(status, symbol);

CREATE TABLE IF NOT EXISTS scanner_runs(
 run_id TEXT PRIMARY KEY,
 started_at TEXT NOT NULL,
 finished_at TEXT NOT NULL,
 symbols_requested INTEGER NOT NULL,
 symbols_succeeded INTEGER NOT NULL,
 symbols_failed INTEGER NOT NULL,
 errors_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scanner_candidates(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 run_id TEXT NOT NULL REFERENCES scanner_runs(run_id) ON DELETE CASCADE,
 rank INTEGER NOT NULL,
 symbol TEXT NOT NULL,
 decision TEXT NOT NULL,
 raw_edge REAL NOT NULL,
 confidence REAL NOT NULL,
 calibrated INTEGER NOT NULL,
 expected_r REAL,
 profit_factor REAL,
 calibration_samples INTEGER NOT NULL,
 stale INTEGER NOT NULL,
 regime TEXT NOT NULL,
 rank_score REAL NOT NULL,
 evaluated_at TEXT NOT NULL,
 UNIQUE(run_id, symbol)
);
CREATE INDEX IF NOT EXISTS idx_scanner_candidates_run_rank
ON scanner_candidates(run_id, rank);

CREATE TABLE IF NOT EXISTS edge_discovery_runs(
 run_id TEXT PRIMARY KEY,
 generated_at TEXT NOT NULL,
 observation_count INTEGER NOT NULL,
 candidate_count INTEGER NOT NULL,
 discovered_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS edge_candidates(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 run_id TEXT NOT NULL REFERENCES edge_discovery_runs(run_id) ON DELETE CASCADE,
 scope TEXT NOT NULL, symbol TEXT, decision TEXT NOT NULL, regime TEXT NOT NULL,
 edge_bucket TEXT NOT NULL, samples INTEGER NOT NULL, win_rate REAL NOT NULL,
 win_rate_lower_95 REAL NOT NULL, expected_r REAL NOT NULL, profit_factor REAL,
 first_half_expected_r REAL NOT NULL, second_half_expected_r REAL NOT NULL,
 stable INTEGER NOT NULL, p_value REAL NOT NULL, q_value REAL NOT NULL,
 discovery_score REAL NOT NULL, status TEXT NOT NULL, reasons_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_edge_candidates_run_score
ON edge_candidates(run_id, status, discovery_score DESC);

CREATE TABLE IF NOT EXISTS monte_carlo_runs(
 run_id TEXT PRIMARY KEY, generated_at TEXT NOT NULL, status TEXT NOT NULL,
 observation_count INTEGER NOT NULL, simulations INTEGER NOT NULL,
 horizon_trades INTEGER NOT NULL, block_size INTEGER NOT NULL, seed INTEGER NOT NULL,
 starting_equity_r REAL NOT NULL, ruin_drawdown_pct REAL NOT NULL,
 expected_final_equity_r REAL, median_final_equity_r REAL, final_equity_p05_r REAL,
 final_equity_p95_r REAL, median_max_drawdown_pct REAL, max_drawdown_p95_pct REAL,
 probability_of_ruin REAL, probability_final_below_start REAL, reason TEXT NOT NULL,
 symbol TEXT, decision TEXT, regime TEXT
);
CREATE INDEX IF NOT EXISTS idx_monte_carlo_generated
ON monte_carlo_runs(generated_at DESC);

CREATE TABLE IF NOT EXISTS walk_forward_runs(
 run_id TEXT PRIMARY KEY, generated_at TEXT NOT NULL, status TEXT NOT NULL,
 observation_count INTEGER NOT NULL, eligible_observations INTEGER NOT NULL,
 folds_requested INTEGER NOT NULL, folds_completed INTEGER NOT NULL,
 passed_folds INTEGER NOT NULL, pass_ratio REAL NOT NULL,
 aggregate_realized_r REAL NOT NULL, aggregate_profit_factor REAL,
 worst_fold_realized_r REAL, reason TEXT NOT NULL,
 symbol TEXT, decision TEXT, regime TEXT, folds_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_walk_forward_generated
ON walk_forward_runs(generated_at DESC);

CREATE TABLE IF NOT EXISTS counterfactual_runs(
 run_id TEXT PRIMARY KEY, generated_at TEXT NOT NULL, status TEXT NOT NULL,
 observation_count INTEGER NOT NULL, scenario_count INTEGER NOT NULL,
 best_scenario TEXT, baseline_realized_r REAL NOT NULL, baseline_profit_factor REAL,
 best_net_benefit_r REAL, reason TEXT NOT NULL, symbol TEXT, decision TEXT,
 regime TEXT, scenarios_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_counterfactual_generated
ON counterfactual_runs(generated_at DESC);

"""

class DatabaseService(BaseService):
    def __init__(self, path: Path) -> None:
        super().__init__("database")
        self._path = path
        self._connection: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        self._state = ServiceState.STARTING
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self._path, check_same_thread=False)
        self._connection.executescript(_SCHEMA)
        self._migrate()
        self._connection.commit()
        self._state = ServiceState.HEALTHY
        self._details = str(self._path)


    def _migrate(self) -> None:
        assert self._connection is not None
        existing = {row[1] for row in self._connection.execute("PRAGMA table_info(portfolio_positions)")}
        migrations = {
            "initial_stop_price": "REAL",
            "highest_price": "REAL",
            "lowest_price": "REAL",
            "partial_taken": "INTEGER NOT NULL DEFAULT 0",
            "partial_realized_pnl": "REAL NOT NULL DEFAULT 0.0",
            "gross_pnl": "REAL NOT NULL DEFAULT 0.0",
            "total_fees": "REAL NOT NULL DEFAULT 0.0",
            "pnl_basis": "TEXT NOT NULL DEFAULT 'NET_AFTER_FEES'",
        }
        for name, ddl in migrations.items():
            if name not in existing:
                self._connection.execute(f"ALTER TABLE portfolio_positions ADD COLUMN {name} {ddl}")

    async def stop(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None
        self._state = ServiceState.STOPPED

    async def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> None:
        if self._connection is None:
            raise RuntimeError("Database is not started")
        async with self._lock:
            self._execute_sync(sql, parameters)

    async def execute_returning_id(self, sql: str, parameters: tuple[object, ...] = ()) -> int:
        if self._connection is None:
            raise RuntimeError("Database is not started")
        async with self._lock:
            cursor = self._connection.execute(sql, parameters)
            self._connection.commit()
            return int(cursor.lastrowid)


    async def transaction(self, statements: list[tuple[str, tuple[object, ...]]]) -> list[int]:
        """Execute statements atomically and return lastrowid values.

        SQLite calls remain serialized by the service lock. A failure rolls back the
        whole unit, preventing position/account divergence after process crashes.
        """
        if self._connection is None:
            raise RuntimeError("Database is not started")
        async with self._lock:
            ids: list[int] = []
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                for sql, parameters in statements:
                    cursor = self._connection.execute(sql, parameters)
                    ids.append(int(cursor.lastrowid or 0))
                self._connection.commit()
                return ids
            except Exception:
                self._connection.rollback()
                raise

    async def fetchall(
        self, sql: str, parameters: tuple[object, ...] = ()
    ) -> list[tuple[object, ...]]:
        if self._connection is None:
            raise RuntimeError("Database is not started")
        async with self._lock:
            return self._fetchall_sync(sql, parameters)

    def _execute_sync(self, sql: str, parameters: tuple[object, ...]) -> None:
        assert self._connection is not None
        self._connection.execute(sql, parameters)
        self._connection.commit()

    def _fetchall_sync(
        self, sql: str, parameters: tuple[object, ...]
    ) -> list[tuple[object, ...]]:
        assert self._connection is not None
        cursor = self._connection.execute(sql, parameters)
        return list(cursor.fetchall())
