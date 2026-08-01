import asyncio
from nexor_x.core.event_bus import EventBus
from nexor_x.domain import Event

async def test_publish_dispatches_event() -> None:
    bus = EventBus()
    received: list[str] = []
    async def handler(event: Event) -> None:
        received.append(event.topic)
    bus.subscribe("market.tick", handler)
    await bus.start()
    await bus.publish(Event("market.tick"))
    await asyncio.wait_for(bus._queue.join(), timeout=1)
    await bus.stop()
    assert received == ["market.tick"]

async def test_handler_failure_does_not_block_other_handlers() -> None:
    bus = EventBus()
    received: list[str] = []
    async def bad(_: Event) -> None:
        raise RuntimeError("expected")
    async def good(event: Event) -> None:
        received.append(event.topic)
    bus.subscribe("x", bad)
    bus.subscribe("x", good)
    await bus.start()
    await bus.publish(Event("x"))
    await asyncio.wait_for(bus._queue.join(), timeout=1)
    await bus.stop()
    assert received == ["x"]
