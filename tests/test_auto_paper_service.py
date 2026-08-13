from __future__ import annotations

import json

import pytest

from nexor_x.autopaper import AutoPaperService


class FakeDatabase:
    def __init__(self) -> None:
        self.cycles = []

    async def execute(self, query, params=()):
        compact = " ".join(str(query).split())
        if compact.startswith("INSERT INTO auto_paper_cycles"):
            self.cycles.append(params)

    async def fetchall(self, query, params=()):
        compact = " ".join(str(query).split())
        if "FROM auto_paper_cycles" in compact and self.cycles:
            payload = self.cycles[-1][2]
            return [(payload,)]
        return []


@pytest.mark.asyncio
async def test_only_approved_candidate_is_opened() -> None:
    async def scanner_run():
        return {
            "candidates": [
                {"symbol": "BTCUSDT"},
                {"symbol": "ETHUSDT"},
            ]
        }

    async def readiness(symbol):
        return {
            "allowed": symbol == "BTCUSDT",
            "reasons": [],
            "context_backtest": {
                "approved": symbol == "BTCUSDT",
            },
        }

    opened = []

    async def paper_open(symbol):
        opened.append(symbol)
        return {"symbol": symbol, "status": "OPEN"}

    async def portfolio():
        return {"open_positions": []}

    service = AutoPaperService(
        FakeDatabase(),
        scanner_run=scanner_run,
        trading_readiness=readiness,
        paper_open=paper_open,
        portfolio_snapshot=portfolio,
        maximum_entries_per_cycle=1,
    )
    result = await service.run_once()

    assert opened == ["BTCUSDT"]
    assert result["opened_positions"] == 1
    assert result["live_execution_allowed"] is False


@pytest.mark.asyncio
async def test_existing_symbol_is_not_duplicated() -> None:
    async def scanner_run():
        return {"candidates": [{"symbol": "BTCUSDT"}]}

    async def readiness(symbol):
        raise AssertionError("Readiness must not run for duplicate symbol")

    async def paper_open(symbol):
        raise AssertionError("Duplicate symbol must not be opened")

    async def portfolio():
        return {
            "open_positions": [
                {"symbol": "BTCUSDT"},
            ]
        }

    service = AutoPaperService(
        FakeDatabase(),
        scanner_run=scanner_run,
        trading_readiness=readiness,
        paper_open=paper_open,
        portfolio_snapshot=portfolio,
    )
    result = await service.run_once()

    assert result["opened_positions"] == 0
    assert result["skipped"][0]["reason"] == "POSICAO_JA_ABERTA"


@pytest.mark.asyncio
async def test_failed_readiness_blocks_entry() -> None:
    async def scanner_run():
        return {"candidates": [{"symbol": "SOLUSDT"}]}

    async def readiness(symbol):
        return {
            "allowed": False,
            "reasons": ["backtest contextual reprovado"],
            "context_backtest": {
                "approved": False,
                "blockers": ["PROFIT_FACTOR"],
            },
        }

    async def paper_open(symbol):
        raise AssertionError("Blocked signal must not be opened")

    async def portfolio():
        return {"open_positions": []}

    service = AutoPaperService(
        FakeDatabase(),
        scanner_run=scanner_run,
        trading_readiness=readiness,
        paper_open=paper_open,
        portfolio_snapshot=portfolio,
    )
    result = await service.run_once()

    assert result["status"] == "NO_ENTRY"
    assert result["opened_positions"] == 0
    assert result["skipped"][0]["reason"] == "GATE_PRE_ENTRADA_REPROVADO"


@pytest.mark.asyncio
async def test_status_persists_last_cycle() -> None:
    database = FakeDatabase()

    async def scanner_run():
        return {"candidates": []}

    async def readiness(symbol):
        return {}

    async def paper_open(symbol):
        return {}

    async def portfolio():
        return {"open_positions": []}

    service = AutoPaperService(
        database,
        scanner_run=scanner_run,
        trading_readiness=readiness,
        paper_open=paper_open,
        portfolio_snapshot=portfolio,
    )
    await service.run_once()
    status = await service.status()

    assert status["latest"]["status"] == "NO_ENTRY"
    assert status["live_execution_allowed"] is False
