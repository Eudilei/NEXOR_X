from datetime import UTC, datetime
from pathlib import Path

import pytest

from nexor_x.config import Settings
from nexor_x.kernel import Kernel
from nexor_x.market.models import MarketSnapshot


@pytest.mark.asyncio
async def test_real_kernel_quant_assessment_exists_and_is_blocked(tmp_path: Path) -> None:
    kernel = Kernel(Settings(nexor_database_path=tmp_path / "nexor.db"))
    await kernel.database.start()

    async def fake_snapshot(symbol: str) -> MarketSnapshot:
        return MarketSnapshot(
            symbol=symbol,
            price=110.0,
            open_price=100.0,
            high_price=112.0,
            low_price=99.0,
            volume=1000.0,
            quote_volume=110000.0,
            price_change_percent=10.0,
            fetched_at=datetime.now(UTC),
            source="test",
        )

    kernel.binance.market_snapshot = fake_snapshot  # type: ignore[method-assign]
    result = await kernel.quant_assessment("BTCUSDT")
    assert result["execution_allowed"] is False
    assert result["calibrated"] is False
    assert result["decision"] in {"LONG_BIAS", "NO_EDGE", "INSUFFICIENT_DATA"}
    await kernel.database.stop()


@pytest.mark.asyncio
async def test_laboratory_status_starts_without_false_certification(tmp_path: Path) -> None:
    kernel = Kernel(Settings(nexor_database_path=tmp_path / "nexor.db"))
    await kernel.database.start()
    status = await kernel.laboratory_status()
    assert status["observation_count"] == 0
    assert status["execution_allowed"] is False
    assert status["live_certified"] is False
    await kernel.database.stop()
