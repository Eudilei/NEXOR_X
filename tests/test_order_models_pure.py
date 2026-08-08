import pytest
from nexor_x.orders import OrderSide, OrderType, TestnetOrderRequest

def test_market_validation():
    request = TestnetOrderRequest(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.01,
    )
    assert request.normalized().symbol == "BTCUSDT"

def test_limit_requires_price():
    with pytest.raises(ValueError):
        TestnetOrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.01,
        ).normalized()
