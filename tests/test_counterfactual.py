from datetime import UTC, datetime, timedelta

import pytest

from nexor_x.infrastructure.database import DatabaseService
from nexor_x.laboratory.counterfactual import CounterfactualConfig, CounterfactualEngine
from nexor_x.laboratory.models import OutcomeObservation


def observations(count: int = 120):
    rows = []
    for i in range(count):
        edge = 0.6 if i % 2 == 0 else 0.1
        realized = 1.0 if edge >= 0.5 else -0.5
        rows.append(OutcomeObservation(
            "BTCUSDT", "LONG_BIAS", edge, "TREND_UP", realized,
            datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=i),
        ))
    return rows


@pytest.mark.asyncio
async def test_counterfactual_finds_historical_improvement(tmp_path):
    db = DatabaseService(tmp_path / "cf.db")
    await db.start()
    engine = CounterfactualEngine(db)
    report = await engine.run(observations(), CounterfactualConfig())
    assert report.status == "IMPROVEMENT_FOUND"
    assert report.best_scenario is not None
    assert report.best_net_benefit_r is not None and report.best_net_benefit_r > 0
    assert report.to_dict()["causal_claim"] is False
    latest = await engine.latest()
    assert latest["run_id"] == report.run_id
    assert latest["execution_allowed"] is False
    await db.stop()


@pytest.mark.asyncio
async def test_counterfactual_insufficient_data(tmp_path):
    db = DatabaseService(tmp_path / "cf.db")
    await db.start()
    engine = CounterfactualEngine(db)
    report = await engine.run(observations(20), CounterfactualConfig(minimum_observations=60))
    assert report.status == "INSUFFICIENT_DATA"
    await db.stop()
