from pathlib import Path

import pytest

from nexor_x.domain import OperatingMode
from nexor_x.execution import PaperExecutionService
from nexor_x.infrastructure.database import DatabaseService
from nexor_x.portfolio import PortfolioService


@pytest.mark.asyncio
async def test_blocked_readiness_never_creates_position(tmp_path: Path) -> None:
    db = DatabaseService(tmp_path / "x.db")
    await db.start()
    svc = PaperExecutionService(db, fee_rate=.0005, slippage_rate=.0003, stop_loss_pct=.01, max_notional_multiple=15)
    fill = await svc.open_from_readiness(mode=OperatingMode.PAPER, readiness={"symbol":"BTCUSDT","allowed":False,"decision":"BLOCKED"}, market={"snapshot":{"price":100,"stale":False}}, portfolio={"equity":100})
    assert fill.status.value == "REJECTED"
    assert await db.fetchall("SELECT COUNT(*) FROM portfolio_positions") == [(0,)]
    await db.stop()


@pytest.mark.asyncio
async def test_paper_open_close_updates_equity(tmp_path: Path) -> None:
    db = DatabaseService(tmp_path / "x.db")
    await db.start()
    portfolio = PortfolioService(db, 100)
    await portfolio.ensure_account()
    svc = PaperExecutionService(db, fee_rate=.0005, slippage_rate=0, stop_loss_pct=.01, max_notional_multiple=15)
    readiness={"symbol":"BTCUSDT","side":"LONG","allowed":True,"decision":"READY_FOR_PAPER","risk_budget":10,"leverage":15}
    fill = await svc.open_from_readiness(mode=OperatingMode.PAPER, readiness=readiness, market={"snapshot":{"price":100,"stale":False}}, portfolio=await portfolio.snapshot())
    assert fill.status.value == "FILLED"
    assert fill.position_id is not None
    closed = await svc.close_position(fill.position_id, 101, "TEST")
    assert closed["net_pnl"] > 0
    snap = await portfolio.snapshot()
    assert snap["open_positions"] == 0
    assert snap["equity"] > 100
    await db.stop()


@pytest.mark.asyncio
async def test_live_is_always_rejected(tmp_path: Path) -> None:
    db = DatabaseService(tmp_path / "x.db")
    await db.start()
    svc = PaperExecutionService(db, fee_rate=0, slippage_rate=0, stop_loss_pct=.01, max_notional_multiple=15)
    fill = await svc.open_from_readiness(mode=OperatingMode.LIVE, readiness={"symbol":"BTCUSDT","side":"LONG","allowed":True,"decision":"READY_FOR_PAPER","risk_budget":10,"leverage":15}, market={"snapshot":{"price":100,"stale":False}}, portfolio={"equity":100})
    assert fill.status.value == "REJECTED"
    assert fill.to_dict()["live_order_sent"] is False
    await db.stop()
