from datetime import UTC, datetime

import pytest

from nexor_x.market.engine import MarketIntelligenceEngine
from nexor_x.market.models import MarketRegime, MarketSnapshot


def snap(change: float, high: float, low: float, open_: float = 100.0, stale: bool = False):
    return MarketSnapshot(
        symbol="BTCUSDT",
        price=100 + change,
        open_price=open_,
        high_price=high,
        low_price=low,
        volume=1000,
        quote_volume=100000,
        price_change_percent=change,
        fetched_at=datetime.now(UTC),
        source="test",
        stale=stale,
    )


@pytest.mark.parametrize(
    ("snapshot", "expected"),
    [
        (snap(1.5, 102, 99), MarketRegime.TREND_UP),
        (snap(-1.5, 101, 98), MarketRegime.TREND_DOWN),
        (snap(0.1, 100.2, 99.9), MarketRegime.COMPRESSION),
        (snap(0.5, 104, 99), MarketRegime.EXPANSION),
        (snap(0.5, 101, 99.5), MarketRegime.RANGE),
    ],
)
def test_regimes(snapshot, expected):
    assert MarketIntelligenceEngine().classify(snapshot).regime is expected


def test_stale_reduces_confidence():
    engine = MarketIntelligenceEngine()
    fresh = engine.classify(snap(2.0, 103, 99, stale=False))
    stale = engine.classify(snap(2.0, 103, 99, stale=True))
    assert stale.confidence < fresh.confidence
    assert "desatualizados" in " ".join(stale.rationale)


def test_snapshot_serialization_has_range():
    data = snap(1.0, 103, 99).to_dict()
    assert data["intraday_range_percent"] == pytest.approx(4.0)
    assert data["symbol"] == "BTCUSDT"
