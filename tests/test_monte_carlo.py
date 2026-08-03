from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from nexor_x.infrastructure.database import DatabaseService
from nexor_x.laboratory.models import OutcomeObservation
from nexor_x.laboratory.monte_carlo import MonteCarloConfig, MonteCarloEngine


def observations(values: list[float]) -> list[OutcomeObservation]:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    return [
        OutcomeObservation(
            symbol="BTCUSDT", decision="LONG_BIAS", raw_edge=0.4,
            regime="TREND_UP", realized_r=value, closed_at=base + timedelta(minutes=i),
        )
        for i, value in enumerate(values)
    ]


@pytest.mark.asyncio
async def test_insufficient_data_is_explicit_and_persisted(tmp_path):
    db = DatabaseService(tmp_path / "db.sqlite")
    await db.start()
    engine = MonteCarloEngine(db, minimum_observations=60)
    report = await engine.run(observations([1.0] * 20), MonteCarloConfig(simulations=100))
    assert report.status == "INSUFFICIENT_DATA"
    assert report.probability_of_ruin is None
    assert (await engine.latest())["status"] == "INSUFFICIENT_DATA"
    await db.stop()


@pytest.mark.asyncio
async def test_positive_distribution_is_reproducible(tmp_path):
    db = DatabaseService(tmp_path / "db.sqlite")
    await db.start()
    engine = MonteCarloEngine(db, minimum_observations=60)
    values = [1.2, 0.8, -0.5, 1.0, -0.4] * 20
    cfg = MonteCarloConfig(simulations=300, horizon_trades=100, block_size=5, seed=7)
    one = await engine.run(observations(values), cfg)
    two = await engine.run(observations(values), cfg)
    assert one.median_final_equity_r == two.median_final_equity_r
    assert one.probability_of_ruin == two.probability_of_ruin
    assert one.status == "ROBUST"
    await db.stop()


@pytest.mark.asyncio
async def test_losing_distribution_is_rejected(tmp_path):
    db = DatabaseService(tmp_path / "db.sqlite")
    await db.start()
    engine = MonteCarloEngine(db, minimum_observations=60)
    values = [-1.2, -0.8, 0.2, -1.0, 0.1] * 20
    report = await engine.run(
        observations(values),
        MonteCarloConfig(simulations=300, horizon_trades=100, block_size=5, seed=9),
    )
    assert report.status == "REJECTED"
    assert report.probability_final_below_start > 0.9
    assert report.to_dict()["live_certified"] is False
    await db.stop()


def test_moving_block_preserves_contiguous_values():
    import random

    result = MonteCarloEngine._moving_block_sample([1, 2, 3, 4, 5], 6, 2, random.Random(2))
    assert len(result) == 6
    for index in range(0, 6, 2):
        pair = result[index:index+2]
        if len(pair) == 2:
            assert pair[1] - pair[0] == 1


def test_invalid_configuration_is_rejected():
    with pytest.raises(ValueError):
        MonteCarloConfig(simulations=99).validate()
