from pathlib import Path
import pytest
from nexor_x.domain import OperatingMode
from nexor_x.execution import PaperExecutionService
from nexor_x.infrastructure.database import DatabaseService
from nexor_x.portfolio import PortfolioService
from nexor_x.position.service import PositionManagementService, PositionPolicy

async def opened(tmp_path: Path):
    db=DatabaseService(tmp_path/'x.db'); await db.start()
    portfolio=PortfolioService(db,100); await portfolio.ensure_account()
    execution=PaperExecutionService(db,fee_rate=0,slippage_rate=0,stop_loss_pct=.01,max_notional_multiple=15)
    fill=await execution.open_from_readiness(mode=OperatingMode.PAPER,
        readiness={'symbol':'BTCUSDT','side':'LONG','allowed':True,'decision':'READY_FOR_PAPER','risk_budget':10,'leverage':15},
        market={'snapshot':{'price':100,'stale':False}},portfolio=await portfolio.snapshot())
    return db,portfolio,execution,fill.position_id

@pytest.mark.asyncio
async def test_break_even_and_partial(tmp_path: Path):
    db,portfolio,execution,pid=await opened(tmp_path)
    svc=PositionManagementService(db,execution,PositionPolicy())
    result=await svc.evaluate(pid,101.6)
    types=[x['type'] for x in result['actions']]
    assert 'MOVE_STOP' in types and 'PARTIAL_CLOSE' in types
    snap=await portfolio.snapshot()
    assert snap['positions'][0]['quantity'] < 15
    await db.stop()

@pytest.mark.asyncio
async def test_trailing_only_improves_stop(tmp_path: Path):
    db,_,execution,pid=await opened(tmp_path)
    svc=PositionManagementService(db,execution,PositionPolicy())
    first=await svc.evaluate(pid,102.5)
    stop1=first['stop_price']
    second=await svc.evaluate(pid,102.1)
    assert second['stop_price'] >= stop1
    await db.stop()

@pytest.mark.asyncio
async def test_protective_stop_closes(tmp_path: Path):
    db,portfolio,execution,pid=await opened(tmp_path)
    svc=PositionManagementService(db,execution,PositionPolicy())
    result=await svc.evaluate(pid,98.9)
    assert result['closed'] is True
    assert (await portfolio.snapshot())['open_positions'] == 0
    await db.stop()
