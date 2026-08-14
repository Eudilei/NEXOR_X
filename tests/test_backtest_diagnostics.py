from pathlib import Path

import pytest

from nexor_x.infrastructure.database import DatabaseService
from nexor_x.laboratory.backtest_diagnostics import BacktestDiagnosticEngine


@pytest.mark.asyncio
async def test_diagnoses_cost_regime_and_profit_protection(tmp_path: Path) -> None:
    database = DatabaseService(tmp_path / "diagnostics.db")
    await database.start()
    engine = BacktestDiagnosticEngine(database)
    report = await engine.diagnose([
        {
            "trade_id": "T-1",
            "symbol": "BTCUSDT",
            "strategy_id": "TREND_PULLBACK",
            "regime": "RANGE",
            "signal_regime": "TREND",
            "gross_pnl": 1.0,
            "entry_fee": 0.6,
            "exit_fee": 0.5,
            "net_pnl": -0.1,
            "realized_r": -0.1,
            "mfe_r": 1.2,
            "mae_r": 0.9,
            "planned_rr": 1.2,
            "slippage_bps": 12,
            "exit_reason": "STOP_LOSS",
        }
    ])
    summary = report["summary"]
    assert summary["pnl_basis"] == "NET_AFTER_FEES"
    assert summary["net_pnl"] == pytest.approx(-0.1)
    codes = {item["code"] for item in report["trades"][0]["causes"]}
    assert {
        "COST_DRAG", "EXCESSIVE_SLIPPAGE", "LOW_PLANNED_RR",
        "REGIME_MISMATCH", "PROFIT_NOT_PROTECTED",
    }.issubset(codes)
    assert report["execution_allowed"] is False
    assert report["live_certified"] is False
    latest = await engine.latest()
    assert latest["run_id"] == report["run_id"]
    await database.stop()


@pytest.mark.asyncio
async def test_uses_net_pnl_for_profit_factor_and_rankings(tmp_path: Path) -> None:
    database = DatabaseService(tmp_path / "net.db")
    await database.start()
    engine = BacktestDiagnosticEngine(database)
    report = await engine.diagnose([
        {"symbol": "BTCUSDT", "strategy_id": "A", "regime": "TREND",
         "gross_pnl": 12, "total_fees": 2, "net_pnl": 10, "realized_r": 1},
        {"symbol": "ETHUSDT", "strategy_id": "B", "regime": "RANGE",
         "gross_pnl": -4, "total_fees": 1, "net_pnl": -5, "realized_r": -1},
    ])
    summary = report["summary"]
    assert summary["net_pnl"] == 5
    assert summary["profit_factor_net"] == 2
    assert summary["net_pnl_by_strategy"] == {"A": 10, "B": -5}
    assert any(
        item["code"] == "COST_EFFICIENT"
        for item in summary["top_positive_factors"]
    )
    await database.stop()


@pytest.mark.asyncio
async def test_marks_unexplained_loss_when_evidence_is_missing(tmp_path: Path) -> None:
    database = DatabaseService(tmp_path / "missing.db")
    await database.start()
    engine = BacktestDiagnosticEngine(database)
    report = await engine.diagnose([{"symbol": "SOLUSDT", "net_pnl": -1}])
    trade = report["trades"][0]
    assert trade["diagnostic_confidence"] == "LOW"
    assert trade["causes"][0]["code"] == "UNEXPLAINED_LOSS"
    assert "realized_r" in trade["missing_fields"]
    await database.stop()


@pytest.mark.asyncio
async def test_rejects_empty_backtest(tmp_path: Path) -> None:
    database = DatabaseService(tmp_path / "empty.db")
    await database.start()
    engine = BacktestDiagnosticEngine(database)
    with pytest.raises(ValueError, match="ao menos uma"):
        await engine.diagnose([])
    await database.stop()
