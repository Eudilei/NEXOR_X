from datetime import UTC, datetime

import pytest

from nexor_x.evidence import EvidenceEngine
from nexor_x.market import MarketIntelligenceEngine, MarketSnapshot
from nexor_x.quant import QuantBrain


@pytest.mark.asyncio
async def test_quant_components_integrate() -> None:
    snapshot = MarketSnapshot(
        symbol="BTCUSDT", price=102.0, open_price=100.0, high_price=104.0,
        low_price=99.0, volume=10.0, quote_volume=1020.0,
        price_change_percent=2.0, fetched_at=datetime.now(UTC), source="test",
    )
    state = MarketIntelligenceEngine().classify(snapshot)
    evidences = EvidenceEngine().evaluate(state)
    result = QuantBrain().assess(snapshot.symbol, evidences)
    assert result.symbol == "BTCUSDT"
    assert result.execution_allowed is False
    assert result.to_dict()["evidences"]
