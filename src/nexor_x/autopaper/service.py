from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from typing import Any


@dataclass(frozen=True, slots=True)
class AutoPaperCycleResult:
    status: str
    scanner_candidates: int
    evaluated_candidates: int
    opened_positions: int
    skipped_candidates: int
    errors: int
    opened: tuple[dict[str, Any], ...]
    skipped: tuple[dict[str, Any], ...]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "scanner_candidates": self.scanner_candidates,
            "evaluated_candidates": self.evaluated_candidates,
            "opened_positions": self.opened_positions,
            "skipped_candidates": self.skipped_candidates,
            "errors": self.errors,
            "opened": list(self.opened),
            "skipped": list(self.skipped),
            "created_at": self.created_at,
            "live_execution_allowed": False,
        }


class AutoPaperService:
    """Autonomous PAPER execution loop.

    The service only invokes the existing PAPER path. It does not call TESTNET
    or LIVE order methods. Every candidate must pass the authoritative
    `trading_readiness` path, which includes the contextual pre-entry backtest.
    """

    def __init__(
        self,
        database: Any,
        *,
        scanner_run: Any,
        trading_readiness: Any,
        paper_open: Any,
        portfolio_snapshot: Any,
        maximum_entries_per_cycle: int = 1,
    ) -> None:
        self.database = database
        self.scanner_run = scanner_run
        self.trading_readiness = trading_readiness
        self.paper_open = paper_open
        self.portfolio_snapshot = portfolio_snapshot
        self.maximum_entries_per_cycle = max(
            int(maximum_entries_per_cycle),
            1,
        )

    async def start(self) -> None:
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS auto_paper_cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                opened_positions INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    async def run_once(self) -> dict[str, Any]:
        await self.start()
        scan = await self.scanner_run()
        candidates = list(scan.get("candidates") or [])

        portfolio = await self.portfolio_snapshot()
        open_symbols = self._open_symbols(portfolio)

        opened: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        errors = 0
        evaluated = 0

        for candidate in candidates:
            if len(opened) >= self.maximum_entries_per_cycle:
                break

            symbol = str(candidate.get("symbol") or "").upper()
            if not symbol:
                skipped.append(
                    {
                        "symbol": "",
                        "reason": "CANDIDATO_SEM_SIMBOLO",
                    }
                )
                continue

            if symbol in open_symbols:
                skipped.append(
                    {
                        "symbol": symbol,
                        "reason": "POSICAO_JA_ABERTA",
                    }
                )
                continue

            try:
                readiness = await self.trading_readiness(symbol)
                evaluated += 1

                if not bool(readiness.get("allowed", False)):
                    skipped.append(
                        {
                            "symbol": symbol,
                            "reason": "GATE_PRE_ENTRADA_REPROVADO",
                            "details": list(
                                readiness.get("reasons") or []
                            ),
                            "context_backtest": readiness.get(
                                "context_backtest"
                            ),
                        }
                    )
                    continue

                fill = await self.paper_open(symbol)
                opened.append(
                    {
                        "symbol": symbol,
                        "fill": fill,
                        "context_backtest": readiness.get(
                            "context_backtest"
                        ),
                    }
                )
                open_symbols.add(symbol)

            except Exception as exc:
                errors += 1
                skipped.append(
                    {
                        "symbol": symbol,
                        "reason": "ERRO_NA_AVALIACAO_OU_EXECUCAO",
                        "details": str(exc),
                    }
                )

        created_at = datetime.now(UTC).isoformat()
        result = AutoPaperCycleResult(
            status=(
                "OPENED"
                if opened
                else ("DEGRADED" if errors else "NO_ENTRY")
            ),
            scanner_candidates=len(candidates),
            evaluated_candidates=evaluated,
            opened_positions=len(opened),
            skipped_candidates=len(skipped),
            errors=errors,
            opened=tuple(opened),
            skipped=tuple(skipped),
            created_at=created_at,
        )
        payload = result.to_dict()

        await self.database.execute(
            """
            INSERT INTO auto_paper_cycles(
                status, opened_positions, payload_json, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (
                result.status,
                result.opened_positions,
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                created_at,
            ),
        )
        return payload

    async def status(self) -> dict[str, Any]:
        await self.start()
        rows = await self.database.fetchall(
            """
            SELECT payload_json
            FROM auto_paper_cycles
            ORDER BY id DESC
            LIMIT 1
            """
        )
        latest = None if not rows else json.loads(str(rows[0][0]))
        return {
            "state": "READY",
            "latest": latest,
            "live_execution_allowed": False,
        }

    @staticmethod
    def _open_symbols(
        portfolio: dict[str, Any],
    ) -> set[str]:
        raw_open_positions = portfolio.get("open_positions")
        if isinstance(raw_open_positions, (list, tuple)):
            positions = list(raw_open_positions)
        else:
            positions = list(portfolio.get("positions") or [])
        symbols: set[str] = set()

        for position in positions:
            if not isinstance(position, dict):
                continue
            symbol = str(position.get("symbol") or "").upper()
            if symbol:
                symbols.add(symbol)

        return symbols
