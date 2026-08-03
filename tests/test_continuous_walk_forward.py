from datetime import UTC, datetime, timedelta

import pytest

from nexor_x.infrastructure.database import DatabaseService
from nexor_x.laboratory.calibration import CalibrationEngine
from nexor_x.laboratory.models import OutcomeObservation
from nexor_x.laboratory.walk_forward import ContinuousWalkForwardEngine, WalkForwardConfig


def data(count: int, positive: bool = True):
    return [OutcomeObservation("BTCUSDT", "LONG_BIAS", 0.5, "TREND_UP",
        1.0 if positive or i % 3 else -0.4, datetime(2024,1,1,tzinfo=UTC)+timedelta(hours=i))
        for i in range(count)]

@pytest.mark.asyncio
async def test_walk_forward_persists_and_is_causal(tmp_path):
    db=DatabaseService(tmp_path/"wf.db"); await db.start()
    engine=ContinuousWalkForwardEngine(db, CalibrationEngine(minimum_samples=20))
    report=await engine.run(data(180), WalkForwardConfig(folds=4, minimum_train_observations=60, minimum_test_observations=20))
    assert report.folds_completed >= 3
    assert all(f["train_end"] < f["test_start"] for f in report.folds)
    latest=await engine.latest(); assert latest["run_id"]==report.run_id
    assert latest["execution_allowed"] is False
    await db.stop()

@pytest.mark.asyncio
async def test_walk_forward_insufficient_data(tmp_path):
    db=DatabaseService(tmp_path/"wf.db"); await db.start()
    engine=ContinuousWalkForwardEngine(db, CalibrationEngine(minimum_samples=20))
    report=await engine.run(data(30), WalkForwardConfig(minimum_train_observations=60, minimum_test_observations=20))
    assert report.status=="INSUFFICIENT_DATA"
    await db.stop()
