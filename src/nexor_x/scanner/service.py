from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Iterable
from datetime import UTC, datetime
from uuid import uuid4

from nexor_x.infrastructure.database import DatabaseService

from .models import ScannerCandidate, ScannerRun

AssessmentProvider = Callable[[str], Awaitable[dict[str, object]]]


class MarketScannerService:
    """Concurrent market scanner. It ranks observations but never opens positions."""

    def __init__(
        self,
        database: DatabaseService,
        assessment_provider: AssessmentProvider,
        *,
        symbols: Iterable[str],
        concurrency: int = 4,
        top_candidates: int = 10,
    ) -> None:
        normalized = tuple(dict.fromkeys(self._normalize_symbol(item) for item in symbols))
        if not normalized:
            raise ValueError("Scanner requires at least one symbol")
        if concurrency < 1:
            raise ValueError("Scanner concurrency must be positive")
        if top_candidates < 1:
            raise ValueError("Scanner top_candidates must be positive")
        self._database = database
        self._assessment_provider = assessment_provider
        self._symbols = normalized
        self._concurrency = concurrency
        self._top_candidates = top_candidates
        self._lock = asyncio.Lock()
        self._latest: ScannerRun | None = None
        self._running = False

    @property
    def symbols(self) -> tuple[str, ...]:
        return self._symbols

    @property
    def running(self) -> bool:
        return self._running

    async def run_once(self) -> ScannerRun:
        if self._lock.locked():
            if self._latest is not None:
                return self._latest
            raise RuntimeError("Scanner run already in progress")

        async with self._lock:
            self._running = True
            started_at = datetime.now(UTC)
            run_id = str(uuid4())
            semaphore = asyncio.Semaphore(self._concurrency)

            async def evaluate(symbol: str) -> tuple[ScannerCandidate | None, dict[str, str] | None]:
                async with semaphore:
                    try:
                        assessment = await self._assessment_provider(symbol)
                        market = assessment.get("market")
                        if not isinstance(market, dict):
                            raise ValueError("assessment missing market context")
                        snapshot = market.get("snapshot")
                        if not isinstance(snapshot, dict):
                            raise ValueError("assessment missing market snapshot")
                        candidate = ScannerCandidate(
                            symbol=symbol,
                            decision=str(assessment.get("decision", "INSUFFICIENT_DATA")),
                            raw_edge=float(assessment.get("raw_edge", 0.0)),
                            confidence=float(assessment.get("confidence", 0.0)),
                            calibrated=bool(assessment.get("calibrated", False)),
                            expected_r=self._optional_float(assessment.get("expected_r")),
                            profit_factor=self._optional_float(assessment.get("profit_factor")),
                            calibration_samples=int(assessment.get("calibration_samples", 0)),
                            stale=bool(snapshot.get("stale", True)),
                            regime=str(market.get("regime", "UNKNOWN")),
                            evaluated_at=datetime.now(UTC),
                        )
                        return candidate, None
                    except Exception as exc:
                        return None, {"symbol": symbol, "error": self._compact_error(exc)}

            try:
                results = await asyncio.gather(*(evaluate(symbol) for symbol in self._symbols))
                candidates = [candidate for candidate, _ in results if candidate is not None]
                errors = [error for _, error in results if error is not None]
                candidates.sort(key=lambda item: item.rank_score, reverse=True)
                selected = tuple(candidates[: self._top_candidates])
                finished_at = datetime.now(UTC)
                run = ScannerRun(
                    run_id=run_id,
                    started_at=started_at,
                    finished_at=finished_at,
                    symbols_requested=len(self._symbols),
                    symbols_succeeded=len(candidates),
                    symbols_failed=len(errors),
                    candidates=selected,
                    errors=tuple(errors),
                )
                await self._persist(run)
                self._latest = run
                return run
            finally:
                self._running = False

    async def status(self) -> dict[str, object]:
        if self._latest is None:
            return {
                "running": self._running,
                "configured_symbols": list(self._symbols),
                "last_run": None,
                "execution_triggered": False,
            }
        return {
            "running": self._running,
            "configured_symbols": list(self._symbols),
            "last_run": self._latest.to_dict(),
            "execution_triggered": False,
        }

    async def _persist(self, run: ScannerRun) -> None:
        await self._database.execute(
            """
            INSERT INTO scanner_runs(
                run_id, started_at, finished_at, symbols_requested,
                symbols_succeeded, symbols_failed, errors_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.run_id,
                run.started_at.isoformat(),
                run.finished_at.isoformat(),
                run.symbols_requested,
                run.symbols_succeeded,
                run.symbols_failed,
                json.dumps(list(run.errors), ensure_ascii=False),
            ),
        )
        for rank, candidate in enumerate(run.candidates, start=1):
            await self._database.execute(
                """
                INSERT INTO scanner_candidates(
                    run_id, rank, symbol, decision, raw_edge, confidence,
                    calibrated, expected_r, profit_factor, calibration_samples,
                    stale, regime, rank_score, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    rank,
                    candidate.symbol,
                    candidate.decision,
                    candidate.raw_edge,
                    candidate.confidence,
                    int(candidate.calibrated),
                    candidate.expected_r,
                    candidate.profit_factor,
                    candidate.calibration_samples,
                    int(candidate.stale),
                    candidate.regime,
                    candidate.rank_score,
                    candidate.evaluated_at.isoformat(),
                ),
            )

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        normalized = symbol.upper().replace("/", "").replace("-", "").strip()
        if not normalized.endswith("USDT") or not normalized.isalnum():
            raise ValueError(f"Invalid scanner symbol: {symbol}")
        return normalized

    @staticmethod
    def _optional_float(value: object) -> float | None:
        return None if value is None else float(value)

    @staticmethod
    def _compact_error(exc: Exception) -> str:
        text = str(exc).strip()
        return text[:180] if text else exc.__class__.__name__
