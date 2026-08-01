from __future__ import annotations
import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from contextlib import suppress
from nexor_x.domain import Event
from nexor_x.logging import logger

EventHandler = Callable[[Event], Awaitable[None]]

class EventBus:
    def __init__(self, queue_size: int = 10_000) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=queue_size)
        self._subscriptions: dict[str, list[EventHandler]] = defaultdict(list)
        self._worker: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()
        self._log = logger("event_bus")

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        if handler not in self._subscriptions[topic]:
            self._subscriptions[topic].append(handler)

    async def publish(self, event: Event) -> None:
        await self._queue.put(event)

    async def start(self) -> None:
        if self._worker and not self._worker.done():
            return
        self._stopping.clear()
        self._worker = asyncio.create_task(self._run(), name="nexor-event-bus")

    async def stop(self) -> None:
        self._stopping.set()
        if self._worker:
            await self._queue.join()
            self._worker.cancel()
            with suppress(asyncio.CancelledError):
                await self._worker
            self._worker = None

    async def _run(self) -> None:
        while not self._stopping.is_set() or not self._queue.empty():
            event = await self._queue.get()
            try:
                handlers = self._subscriptions.get(event.topic, []) + self._subscriptions.get("*", [])
                results = await asyncio.gather(
                    *(handler(event) for handler in handlers), return_exceptions=True
                )
                for result in results:
                    if isinstance(result, Exception):
                        self._log.error("event_handler_failed topic=%s error=%s", event.topic, result)
            finally:
                self._queue.task_done()

    @property
    def pending_events(self) -> int:
        return self._queue.qsize()
