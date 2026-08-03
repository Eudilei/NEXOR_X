from pathlib import Path

import pytest

from nexor_x.domain import OperatingMode
from nexor_x.execution import PaperExecutionService
from nexor_x.infrastructure.database import DatabaseService
from nexor_x.portfolio import PortfolioService


@pytest.mark.asyncio
async def test_entry_fee_is_booked_immediately_and_not_double_charged(tmp_path: Path) -> None:
    db = DatabaseService(tmp_path / "x.db")
    await db.start()
    portfolio = PortfolioService(db, 100.0)
    await portfolio.ensure_account()
    service = PaperExecutionService(
        db, fee_rate=0.001, slippage_rate=0.0, stop_loss_pct=0.01, max_notional_multiple=15
    )
    readiness = {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "allowed": True,
        "decision": "READY_FOR_PAPER",
        "risk_budget": 10.0,
        "leverage": 15.0,
    }
    fill = await service.open_from_readiness(
        mode=OperatingMode.PAPER,
        readiness=readiness,
        market={"snapshot": {"price": 100.0, "stale": False}},
        portfolio=await portfolio.snapshot(),
    )
    after_open = await portfolio.snapshot()
    assert after_open["equity"] == pytest.approx(100.0 - fill.fee_paid)
    assert fill.position_id is not None

    closed = await service.close_position(fill.position_id, 100.0, "FLAT")
    after_close = await portfolio.snapshot()
    expected = 100.0 - fill.fee_paid - closed["fees"] + fill.fee_paid
    assert after_close["equity"] == pytest.approx(expected)
    await db.stop()
