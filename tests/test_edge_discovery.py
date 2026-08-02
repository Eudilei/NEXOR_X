from datetime import UTC, datetime, timedelta

import pytest

from nexor_x.infrastructure.database import DatabaseService
from nexor_x.laboratory.edge_discovery import EdgeDiscoveryEngine
from nexor_x.laboratory.models import OutcomeObservation


def observations(count: int, *, profitable: bool = True, symbol: str = "BTCUSDT"):
    base = datetime(2025, 1, 1, tzinfo=UTC)
    result = []
    for index in range(count):
        if profitable:
            realized = 1.2 if index % 3 else -0.5
        else:
            realized = 0.5 if index % 3 == 0 else -1.0
        result.append(OutcomeObservation(
            symbol=symbol, decision="LONG_BIAS", raw_edge=0.62,
            regime="TREND_UP", realized_r=realized,
            closed_at=base + timedelta(hours=index),
        ))
    return result


def test_profitable_stable_context_is_discovered(tmp_path):
    engine = EdgeDiscoveryEngine(DatabaseService(tmp_path / "db.sqlite"), minimum_samples=30)
    candidates = engine.analyze(observations(90))
    assert candidates
    assert any(x.status == "DISCOVERED" for x in candidates)
    assert all(x.stable for x in candidates if x.status == "DISCOVERED")


def test_losing_context_is_rejected(tmp_path):
    engine = EdgeDiscoveryEngine(DatabaseService(tmp_path / "db.sqlite"), minimum_samples=30)
    candidates = engine.analyze(observations(90, profitable=False))
    assert candidates
    assert all(x.status == "REJECTED" for x in candidates)


def test_insufficient_samples_produce_no_candidate(tmp_path):
    engine = EdgeDiscoveryEngine(DatabaseService(tmp_path / "db.sqlite"), minimum_samples=30)
    assert engine.analyze(observations(29)) == []


def test_symbol_and_global_scopes_are_separate(tmp_path):
    engine = EdgeDiscoveryEngine(DatabaseService(tmp_path / "db.sqlite"), minimum_samples=30)
    candidates = engine.analyze(observations(40, symbol="BTCUSDT") + observations(40, symbol="ETHUSDT"))
    scopes = {(x.scope, x.symbol) for x in candidates}
    assert ("GLOBAL", None) in scopes
    assert ("SYMBOL", "BTCUSDT") in scopes
    assert ("SYMBOL", "ETHUSDT") in scopes

@pytest.mark.asyncio
async def test_discovery_is_persisted_and_never_allows_execution(tmp_path):
    database = DatabaseService(tmp_path / "db.sqlite")
    await database.start()
    engine = EdgeDiscoveryEngine(database, minimum_samples=30)
    report = await engine.discover(observations(90))
    assert report["execution_allowed"] is False
    assert report["live_certified"] is False
    latest = await engine.latest()
    assert latest["last_run"]["run_id"] == report["run_id"]
    await database.stop()

@pytest.mark.asyncio
async def test_empty_edge_status(tmp_path):
    database = DatabaseService(tmp_path / "db.sqlite")
    await database.start()
    engine = EdgeDiscoveryEngine(database, minimum_samples=30)
    status = await engine.latest()
    assert status["last_run"] is None
    assert status["execution_allowed"] is False
    await database.stop()
