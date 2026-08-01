from datetime import UTC, datetime, timedelta

import httpx
import pytest

from nexor_x.infrastructure.binance import BinanceMarketDataService
from nexor_x.market.models import MarketSnapshot


def cached_snapshot(*, age_seconds: int = 0) -> MarketSnapshot:
    return MarketSnapshot(
        symbol="BTCUSDT",
        price=60000,
        open_price=59000,
        high_price=61000,
        low_price=58000,
        volume=1,
        quote_volume=1,
        price_change_percent=1.2,
        fetched_at=datetime.now(UTC) - timedelta(seconds=age_seconds),
        source="test",
    )


def test_symbol_validation():
    assert BinanceMarketDataService._normalize_symbol("btc/usdt") == "BTCUSDT"
    with pytest.raises(ValueError):
        BinanceMarketDataService._normalize_symbol("BTCUSD")


def test_parse_snapshot():
    payload = {
        "lastPrice": "10",
        "openPrice": "9",
        "highPrice": "11",
        "lowPrice": "8",
        "volume": "100",
        "quoteVolume": "1000",
        "priceChangePercent": "11.1",
    }
    result = BinanceMarketDataService._parse_snapshot("BTCUSDT", payload, datetime.now(UTC))
    assert result.price == 10
    assert result.source == "Binance Futures 24h"


def test_cached_data_is_marked_stale():
    service = BinanceMarketDataService(stale_after_seconds=10)
    service._cache["BTCUSDT"] = cached_snapshot(age_seconds=20)
    result = service._cached_or_raise("BTCUSDT", datetime.now(UTC))
    assert result.stale is True
    assert result.source.endswith(":cache")


def test_no_cache_raises_compact_error():
    service = BinanceMarketDataService()
    service._last_error = "HTTP 451"
    with pytest.raises(RuntimeError, match="HTTP 451"):
        service._cached_or_raise("BTCUSDT", datetime.now(UTC))


def test_http_error_is_compact():
    request = httpx.Request("GET", "https://example.test")
    response = httpx.Response(451, request=request)
    exc = httpx.HTTPStatusError("blocked", request=request, response=response)
    assert BinanceMarketDataService._compact_error(exc) == "HTTP 451"
