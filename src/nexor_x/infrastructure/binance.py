from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from nexor_x.core.service import BaseService
from nexor_x.domain import ServiceState
from nexor_x.market.models import MarketSnapshot


class BinanceMarketDataService(BaseService):
    """Read-only Binance Futures adapter with cache, cooldown and graceful degradation."""

    def __init__(
        self,
        testnet: bool = False,
        *,
        cache_ttl_seconds: float = 15.0,
        stale_after_seconds: float = 120.0,
        failure_cooldown_seconds: float = 60.0,
    ) -> None:
        super().__init__("binance_market_data")
        self._base_url = (
            "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"
        )
        self._client: httpx.AsyncClient | None = None
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._stale_after = timedelta(seconds=stale_after_seconds)
        self._failure_cooldown = timedelta(seconds=failure_cooldown_seconds)
        self._cache: dict[str, MarketSnapshot] = {}
        self._last_failure_at: datetime | None = None
        self._last_error = ""
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(8.0, connect=5.0),
            headers={"User-Agent": "NEXOR-X/0.4"},
        )
        await self._probe()

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._state = ServiceState.STOPPED

    async def _probe(self) -> None:
        if self._client is None:
            return
        try:
            response = await self._client.get("/fapi/v1/ping")
            response.raise_for_status()
            self._state = ServiceState.HEALTHY
            self._details = "public futures API connected"
            self._last_error = ""
        except Exception as exc:
            self._mark_failure(exc)

    def _mark_failure(self, exc: Exception) -> None:
        self._last_failure_at = datetime.now(UTC)
        self._last_error = self._compact_error(exc)
        self._state = ServiceState.DEGRADED
        self._details = f"degraded: {self._last_error}"

    @staticmethod
    def _compact_error(exc: Exception) -> str:
        if isinstance(exc, httpx.HTTPStatusError):
            return f"HTTP {exc.response.status_code}"
        return exc.__class__.__name__

    def _in_cooldown(self, now: datetime) -> bool:
        return bool(
            self._last_failure_at and now - self._last_failure_at < self._failure_cooldown
        )

    async def market_snapshot(self, symbol: str = "BTCUSDT") -> MarketSnapshot:
        normalized = self._normalize_symbol(symbol)
        now = datetime.now(UTC)
        cached = self._cache.get(normalized)
        if cached and now - cached.fetched_at <= self._cache_ttl:
            return cached
        if self._in_cooldown(now):
            return self._cached_or_raise(normalized, now)

        async with self._lock:
            now = datetime.now(UTC)
            cached = self._cache.get(normalized)
            if cached and now - cached.fetched_at <= self._cache_ttl:
                return cached
            if self._in_cooldown(now):
                return self._cached_or_raise(normalized, now)
            if self._client is None:
                raise RuntimeError("Binance service is not started")
            try:
                response = await self._client.get(
                    "/fapi/v1/ticker/24hr", params={"symbol": normalized}
                )
                response.raise_for_status()
                snapshot = self._parse_snapshot(normalized, response.json(), now)
                self._cache[normalized] = snapshot
                self._state = ServiceState.HEALTHY
                self._details = "real futures data; cache active"
                self._last_error = ""
                self._last_failure_at = None
                return snapshot
            except Exception as exc:
                self._mark_failure(exc)
                return self._cached_or_raise(normalized, now)

    async def ticker_price(self, symbol: str = "BTCUSDT") -> float:
        return (await self.market_snapshot(symbol)).price

    def _cached_or_raise(self, symbol: str, now: datetime) -> MarketSnapshot:
        cached = self._cache.get(symbol)
        if cached is None:
            detail = self._last_error or "market data unavailable"
            raise RuntimeError(detail)
        is_stale = now - cached.fetched_at > self._stale_after
        return replace(cached, stale=is_stale, source=f"{cached.source}:cache")

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        normalized = symbol.upper().replace("/", "").replace("-", "").strip()
        if not normalized.endswith("USDT") or not normalized.isalnum():
            raise ValueError("Simbolo invalido")
        return normalized

    @staticmethod
    def _parse_snapshot(
        symbol: str, payload: dict[str, Any], fetched_at: datetime
    ) -> MarketSnapshot:
        return MarketSnapshot(
            symbol=symbol,
            price=float(payload["lastPrice"]),
            open_price=float(payload["openPrice"]),
            high_price=float(payload["highPrice"]),
            low_price=float(payload["lowPrice"]),
            volume=float(payload["volume"]),
            quote_volume=float(payload["quoteVolume"]),
            price_change_percent=float(payload["priceChangePercent"]),
            fetched_at=fetched_at,
            source="Binance Futures 24h",
            stale=False,
        )

    def diagnostics(self) -> dict[str, Any]:
        return {
            "base_url": self._base_url,
            "cached_symbols": sorted(self._cache),
            "last_error": self._last_error,
            "cooldown_active": self._in_cooldown(datetime.now(UTC)),
        }
