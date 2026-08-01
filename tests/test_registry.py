import pytest
from nexor_x.core.registry import ServiceRegistry
from nexor_x.core.service import BaseService
from nexor_x.domain import ServiceState

class Dummy(BaseService):
    def __init__(self) -> None:
        super().__init__("dummy")
    async def start(self) -> None:
        self._state = ServiceState.HEALTHY
    async def stop(self) -> None:
        self._state = ServiceState.STOPPED

async def test_registry_rejects_duplicate() -> None:
    registry = ServiceRegistry()
    await registry.register(Dummy())
    with pytest.raises(ValueError):
        await registry.register(Dummy())
