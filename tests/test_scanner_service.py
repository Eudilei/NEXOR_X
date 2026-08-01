from __future__ import annotations

from pathlib import Path

import pytest

from nexor_x.infrastructure.database import DatabaseService
from nexor_x.scanner import MarketScannerService


def assessment(symbol: str, edge: float, *, stale: bool = False) -> dict[str, object]:
    return {
        "symbol": symbol,
        "decision": "LONG_BIAS" if edge >= 0 else "SHORT_BIAS",
        "raw_edge": edge,
        "confidence": abs(edge),
        "calibrated": False,
        "expected_r": None,
        "profit_factor": None,
        "calibration_samples": 0,
        "market": {
            "regime": "TREND_UP" if edge >= 0 else "TREND_DOWN",
            "snapshot": {"stale": stale},
        },
    }


@pytest.mark.asyncio
async def test_scanner_ranks_candidates_and_persists(tmp_path: Path) -> None:
    database = DatabaseService(tmp_path / "scanner.db")
    await database.start()

    async def provider(symbol: str) -> dict[str, object]:
        return assessment(symbol, {"BTCUSDT": 0.4, "ETHUSDT": -0.8, "SOLUSDT": 0.6}[symbol])

    scanner = MarketScannerService(
        database,
        provider,
        symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        concurrency=2,
        top_candidates=2,
    )
    run = await scanner.run_once()
    assert run.symbols_succeeded == 3
    assert run.symbols_failed == 0
    assert len(run.candidates) == 2
    assert run.candidates[0].symbol == "ETHUSDT"
    assert run.to_dict()["execution_triggered"] is False
    rows = await database.fetchall("SELECT COUNT(*) FROM scanner_candidates")
    assert rows[0][0] == 2
    await database.stop()


@pytest.mark.asyncio
async def test_scanner_isolates_symbol_failures(tmp_path: Path) -> None:
    database = DatabaseService(tmp_path / "scanner.db")
    await database.start()

    async def provider(symbol: str) -> dict[str, object]:
        if symbol == "ETHUSDT":
            raise RuntimeError("upstream unavailable")
        return assessment(symbol, 0.5)

    scanner = MarketScannerService(
        database,
        provider,
        symbols=("BTCUSDT", "ETHUSDT"),
    )
    run = await scanner.run_once()
    assert run.symbols_succeeded == 1
    assert run.symbols_failed == 1
    assert run.errors[0]["symbol"] == "ETHUSDT"
    await database.stop()


def test_scanner_rejects_invalid_configuration(tmp_path: Path) -> None:
    database = DatabaseService(tmp_path / "scanner.db")

    async def provider(symbol: str) -> dict[str, object]:
        return assessment(symbol, 0.5)

    with pytest.raises(ValueError):
        MarketScannerService(database, provider, symbols=())
    with pytest.raises(ValueError):
        MarketScannerService(database, provider, symbols=("BTC",))
    with pytest.raises(ValueError):
        MarketScannerService(database, provider, symbols=("BTCUSDT",), concurrency=0)


def test_stale_candidate_receives_rank_penalty() -> None:
    from datetime import UTC, datetime
    from nexor_x.scanner import ScannerCandidate

    fresh = ScannerCandidate(
        "BTCUSDT", "LONG_BIAS", 0.5, 0.5, False, None, None, 0,
        False, "TREND_UP", datetime.now(UTC),
    )
    stale = ScannerCandidate(
        "BTCUSDT", "LONG_BIAS", 0.5, 0.5, False, None, None, 0,
        True, "TREND_UP", datetime.now(UTC),
    )
    assert fresh.rank_score > stale.rank_score
