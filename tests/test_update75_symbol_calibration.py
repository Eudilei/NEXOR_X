from datetime import UTC, datetime

import pytest

from nexor_x.laboratory.service import LaboratoryService


class FakeDatabase:
    def __init__(self) -> None:
        self.calls = []

    async def fetchall(self, query, params=()):
        self.calls.append((query, params))
        now = datetime.now(UTC).isoformat()
        return [("BTCUSDT", "LONG_BIAS", .5, "TREND_UP", 1.0, now)]


@pytest.mark.asyncio
async def test_calibration_queries_only_requested_symbol():
    database = FakeDatabase()
    service = LaboratoryService(database, minimum_samples=5)
    estimate = await service.estimate(
        .5, "LONG_BIAS", "TREND_UP", symbol="BTCUSDT"
    )
    assert database.calls[0][1] == ("BTCUSDT",)
    assert "UPPER(symbol)=?" in database.calls[0][0]
    assert estimate.sample_count == 1
