from abc import ABC, abstractmethod
from nexor_x.domain import ServiceHealth, ServiceState

class Service(ABC):
    name: str
    @abstractmethod
    async def start(self) -> None: ...
    @abstractmethod
    async def stop(self) -> None: ...
    @abstractmethod
    async def health(self) -> ServiceHealth: ...

class BaseService(Service):
    def __init__(self, name: str) -> None:
        self.name = name
        self._state = ServiceState.STOPPED
        self._details = ""

    async def health(self) -> ServiceHealth:
        return ServiceHealth(self.name, self._state, self._details)
