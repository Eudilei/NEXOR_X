from __future__ import annotations

from datetime import UTC, datetime

from nexor_x.market.models import MarketSnapshot
from nexor_x.scanner.universe import ShallowUniverseSelector


def test_shallow_stage_limits_deep_universe_to_sixty() -> None:
    snapshots = [MarketSnapshot(
        symbol=f"ASSET{index}USDT", price=10, open_price=9, high_price=11, low_price=8,
        volume=1_000, quote_volume=2_000_000+index*100_000,
        price_change_percent=float(index % 10), fetched_at=datetime.now(UTC),
        source="test", stale=False,
    ) for index in range(100)]
    selected = ShallowUniverseSelector(limit=60).select(snapshots)
    assert len(selected) == 60
    assert len({item.symbol for item in selected}) == 60


def test_shallow_stage_rejects_stale_and_illiquid_assets() -> None:
    base = dict(price=10, open_price=9, high_price=11, low_price=8, volume=1_000,
                price_change_percent=2, fetched_at=datetime.now(UTC), source="test")
    snapshots = [
        MarketSnapshot(symbol="GOODUSDT", quote_volume=5_000_000, stale=False, **base),
        MarketSnapshot(symbol="STALEUSDT", quote_volume=5_000_000, stale=True, **base),
        MarketSnapshot(symbol="THINUSDT", quote_volume=100, stale=False, **base),
    ]
    assert [item.symbol for item in ShallowUniverseSelector().select(snapshots)] == ["GOODUSDT"]
