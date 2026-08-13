from __future__ import annotations
import pytest
from nexor_x.automanage import AutoPositionManagementService

class FakeDatabase:
    def __init__(self): self.cycles=[]
    async def execute(self, query, params=()):
        if "INSERT INTO auto_position_management_cycles" in " ".join(str(query).split()): self.cycles.append(params)
    async def fetchall(self, query, params=()):
        if "FROM auto_position_management_cycles" in " ".join(str(query).split()) and self.cycles: return [(self.cycles[-1][3],)]
        return []

@pytest.mark.asyncio
async def test_cycle_counts_actions_and_closures():
    async def manage_all():
        return {"evaluated":2,"skipped":[],"positions":[
            {"actions":[{"type":"MOVE_STOP"},{"type":"PARTIAL_CLOSE"}],"closed":False},
            {"actions":[{"type":"CLOSE"}],"closed":True},]}
    result=await AutoPositionManagementService(FakeDatabase(),manage_all).run_once()
    assert result["evaluated_positions"]==2
    assert result["action_count"]==3
    assert result["closed_positions"]==1
    assert result["live_execution_allowed"] is False

@pytest.mark.asyncio
async def test_status_persists_latest_cycle():
    db=FakeDatabase()
    async def manage_all(): return {"evaluated":0,"skipped":[],"positions":[]}
    s=AutoPositionManagementService(db,manage_all)
    await s.run_once(); status=await s.status()
    assert status["latest"]["evaluated_positions"]==0
