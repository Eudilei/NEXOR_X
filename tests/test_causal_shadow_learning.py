from nexor_x.shadow import CausalShadowLearningService


def service() -> CausalShadowLearningService:
    return CausalShadowLearningService(
        None, quant_assessment=None, market_state=None, symbols=("BTCUSDT",),
        fee_rate=0.0005, slippage_rate=0.0003, stop_loss_pct=0.01,
        break_even_trigger_r=0.8, break_even_buffer_r=0.05,
        partial_trigger_r=1.5, partial_fraction=0.35,
        trailing_start_r=2.0, trailing_distance_r=0.8,
    )


def test_shadow_never_creates_order_and_closes_causally() -> None:
    engine = service()
    position = {
        "side": "LONG", "entry_price": 100.0, "stop_price": 99.0,
        "highest_price": 100.0, "lowest_price": 100.0,
        "partial_taken": 0, "remaining_fraction": 1.0, "partial_net_r": 0.0,
    }
    advanced = engine.advance_position(position, 101.6)
    assert not advanced.closed
    assert advanced.partial_taken
    assert advanced.remaining_fraction == 0.65
    closed = engine.advance_position({**position,
        "stop_price": advanced.stop_price, "highest_price": advanced.highest_price,
        "lowest_price": advanced.lowest_price, "partial_taken": 1,
        "remaining_fraction": advanced.remaining_fraction,
        "partial_net_r": advanced.partial_net_r}, advanced.stop_price)
    assert closed.closed
    assert closed.realized_r is not None
