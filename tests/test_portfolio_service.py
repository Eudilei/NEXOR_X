from pathlib import Path

import pytest

from nexor_x.infrastructure.database import DatabaseService
from nexor_x.portfolio import PortfolioService


@pytest.mark.asyncio
async def test_portfolio_initializes_single_account(tmp_path: Path):
    db = DatabaseService(tmp_path / "portfolio.db")
    await db.start()
    try:
        service = PortfolioService(db, 100.0)
        first = await service.snapshot()
        second = await service.snapshot()
        assert first["equity"] == 100.0
        assert first["peak_equity"] == 100.0
        assert first["drawdown_pct"] == 0.0
        assert first["open_positions"] == 0
        rows = await db.fetchall("SELECT COUNT(*) FROM portfolio_accounts")
        assert rows[0][0] == 1
        assert second["equity"] == 100.0
    finally:
        await db.stop()


@pytest.mark.asyncio
async def test_portfolio_computes_drawdown_and_exposure(tmp_path: Path):
    db = DatabaseService(tmp_path / "portfolio.db")
    await db.start()
    try:
        service = PortfolioService(db, 100.0)
        await service.ensure_account()
        await db.execute(
            "UPDATE portfolio_accounts SET equity=80.0, peak_equity=100.0 WHERE account_id='PAPER'"
        )
        await db.execute(
            """INSERT INTO portfolio_positions
            (symbol, side, quantity, entry_price, notional, status, opened_at)
            VALUES ('BTCUSDT','LONG',0.01,50000,500,'OPEN','2026-01-01T00:00:00+00:00')"""
        )
        result = await service.snapshot()
        assert result["drawdown_pct"] == 20.0
        assert result["open_positions"] == 1
        assert result["gross_notional"] == 500.0
    finally:
        await db.stop()
