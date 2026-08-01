from __future__ import annotations
import httpx
from nexor_x.core.service import BaseService
from nexor_x.domain import ServiceState

SYSTEM_PROMPT = """You are the local NEXOR X quantitative operations assistant.
Be factual and explicit about uncertainty. Never claim guaranteed profit or authorize LIVE trading."""

class OllamaService(BaseService):
    def __init__(self, base_url: str, model: str) -> None:
        super().__init__("ollama")
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(timeout=45.0)
        try:
            response = await self._client.get(f"{self._base_url}/api/tags")
            response.raise_for_status()
            self._state = ServiceState.HEALTHY
            self._details = f"model={self._model}"
        except Exception as exc:
            self._state = ServiceState.DEGRADED
            self._details = f"Ollama unavailable: {exc}"

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._state = ServiceState.STOPPED

    async def chat(self, message: str, context: str = "") -> str:
        if self._client is None:
            raise RuntimeError("Ollama service is not started")
        if (await self.health()).state is not ServiceState.HEALTHY:
            return "Ollama está offline. Inicie o Ollama e confirme o modelo configurado no .env."
        response = await self._client.post(
            f"{self._base_url}/api/chat",
            json={
                "model": self._model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT + "\\n" + context},
                    {"role": "user", "content": message},
                ],
            },
        )
        response.raise_for_status()
        return str(response.json()["message"]["content"])
