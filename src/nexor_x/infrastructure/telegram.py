from __future__ import annotations
import httpx
from nexor_x.core.service import BaseService
from nexor_x.domain import ServiceState

class TelegramService(BaseService):
    def __init__(self, token: str, chat_id: str) -> None:
        super().__init__("telegram")
        self._token = token.strip()
        self._chat_id = chat_id.strip()
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(timeout=8.0)
        if not self._token or not self._chat_id:
            self._state = ServiceState.DEGRADED
            self._details = "not configured"
            return
        self._state = ServiceState.HEALTHY
        self._details = "configured"

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._state = ServiceState.STOPPED

    async def send(self, message: str) -> bool:
        if not self._token or not self._chat_id or self._client is None:
            return False
        response = await self._client.post(
            f"https://api.telegram.org/bot{self._token}/sendMessage",
            json={"chat_id": self._chat_id, "text": message},
        )
        response.raise_for_status()
        return True
