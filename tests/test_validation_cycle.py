from __future__ import annotations

from dataclasses import dataclass

import pytest

from nexor_x.validation_cycle import ValidationCycleService


@dataclass
class Snapshot:
    paper_trades: int = 250
    profit_factor: float = 1.25
    expected_r: float = 0.04
    drawdown_pct: float = 8.0
    recent_profit_factor: float = 1.15
    recent_expected_r: float = 0.02
    operational_incidents: int = 0
    critical_test_failures: int = 0
    integration_healthy: bool = True
    recovery_ok: bool = True
    supervisor_paper_allowed: bool = True
    supervisor_testnet_allowed: bool = True

    def to_dict(self):
        return dict(self.__dict__)


class FakeCollector:
    async def collect(self):
        return Snapshot()


class FakeCampaign:
    def __init__(self):
        self.payload = None

    async def evaluate(self, payload):
        self.payload = payload
        return {
            "phase": "VALIDATION_IN_PROGRESS",
            "continue_campaign": True,
            "paper_allowed": True,
            "testnet_allowed": True,
            "live_allowed": False,
        }


class FakeDatabase:
    def __init__(self):
        self.started_at = None
        self.runs = []

    async def execute(self, query, params=()):
        compact = " ".join(str(query).split())
        if compact.startswith(
            "INSERT INTO validation_cycle_state"
        ):
            self.started_at = params[0]
        elif compact.startswith(
            "INSERT INTO validation_cycle_runs"
        ):
            self.runs.append(params)

    async def fetchall(self, query, params=()):
        compact = " ".join(str(query).split())
        if "FROM validation_cycle_state" in compact:
            return [] if self.started_at is None else [(self.started_at,)]
        if "FROM validation_cycle_runs" in compact:
            if not self.runs:
                return []
            row = self.runs[-1]
            return [(row[0], row[1], row[2], row[3])]
        return []


@pytest.mark.asyncio
async def test_cycle_uses_collected_evidence() -> None:
    campaign = FakeCampaign()
    service = ValidationCycleService(
        FakeDatabase(),
        FakeCollector(),
        campaign,
    )
    result = await service.run_once()

    assert result["status"] == "OK"
    assert campaign.payload["paper_trades"] == 250
    assert campaign.payload["days_running"] == 0
    assert result["live_allowed"] is False


@pytest.mark.asyncio
async def test_cycle_persists_latest_result() -> None:
    database = FakeDatabase()
    service = ValidationCycleService(
        database,
        FakeCollector(),
        FakeCampaign(),
    )
    await service.run_once()
    status = await service.status()

    assert status["latest"] is not None
    assert status["latest"]["campaign"]["phase"] == "VALIDATION_IN_PROGRESS"
    assert status["live_allowed"] is False


@pytest.mark.asyncio
async def test_cycle_start_is_stable() -> None:
    database = FakeDatabase()
    service = ValidationCycleService(
        database,
        FakeCollector(),
        FakeCampaign(),
    )
    await service.start()
    first = database.started_at
    await service.start()
    assert database.started_at == first
