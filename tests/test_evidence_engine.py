from datetime import UTC, datetime

from nexor_x.evidence import EvidenceDirection, EvidenceEngine
from nexor_x.market import MarketIntelligenceEngine, MarketSnapshot


def snapshot(change: float = 2.0, stale: bool = False) -> MarketSnapshot:
    return MarketSnapshot(
        symbol="BTCUSDT", price=102.0, open_price=100.0, high_price=103.0,
        low_price=99.0, volume=1000.0, quote_volume=102000.0,
        price_change_percent=change, fetched_at=datetime.now(UTC), source="test", stale=stale,
    )


def test_evidence_is_explainable_and_directional() -> None:
    state = MarketIntelligenceEngine().classify(snapshot())
    items = EvidenceEngine().evaluate(state)
    momentum = next(item for item in items if item.name == "price_momentum")
    assert momentum.direction is EvidenceDirection.BULLISH
    assert momentum.source_fields == ("price_change_percent",)
    assert momentum.signed_value > 0


def test_stale_data_reduces_reliability() -> None:
    engine = EvidenceEngine()
    fresh = engine.evaluate(MarketIntelligenceEngine().classify(snapshot(stale=False)))
    stale = engine.evaluate(MarketIntelligenceEngine().classify(snapshot(stale=True)))
    assert fresh[0].reliability > stale[0].reliability
