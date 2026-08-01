from __future__ import annotations
import httpx
from nexor_x.core.service import BaseService
from nexor_x.domain import ServiceState

class BinanceMarketDataService(BaseService):
    """Read-only Binance Futures market-data adapter for PAPER."""

    def __init__(self, testnet: bool = False) -> None:
        super().__init__("binance_market_data")
        self._base_url = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=8.0)
        try:
            response = await self._client.get("/fapi/v1/ping")
            response.raise_for_status()
            self._state = ServiceState.HEALTHY
            self._details = "public futures API connected"
        except Exception as exc:
            self._state = ServiceState.DEGRADED
            self._details = f"offline at startup: {exc}"

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._state = ServiceState.STOPPED

    async def ticker_price(self, symbol: str = "BTCUSDT") -> float:
        if self._client is None:
            raise RuntimeError("Binance service is not started")
        response = await self._client.get("/fapi/v1/ticker/price", params={"symbol": symbol})
        response.raise_for_status()
        return float(response.json()["price"])
