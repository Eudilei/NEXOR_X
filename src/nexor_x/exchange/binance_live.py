from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlencode

import httpx


@dataclass(frozen=True, slots=True)
class BinanceCredentials:
    api_key: str
    api_secret: str

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip() and self.api_secret.strip())


@dataclass(frozen=True, slots=True)
class BinanceLivePolicy:
    base_url: str = "https://fapi.binance.com"
    testnet_url: str = "https://testnet.binancefuture.com"
    timeout_seconds: float = 10.0
    recv_window_ms: int = 5000
    maximum_time_drift_ms: int = 1000
    use_testnet: bool = True


@dataclass(frozen=True, slots=True)
class BinanceReadinessReport:
    status: str
    credentials_configured: bool
    public_ping_ok: bool
    time_sync_ok: bool
    time_drift_ms: int | None
    signed_account_access_ok: bool
    testnet: bool
    blockers: tuple[str, ...]
    live_order_permission: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        return data


class BinanceLiveConnector:
    """Authenticated Binance Futures connector foundation.

    This class intentionally exposes only read-only readiness methods in Sprint 21.
    No order-creation endpoint exists here.
    """

    def __init__(
        self,
        credentials: BinanceCredentials,
        policy: BinanceLivePolicy | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.credentials = credentials
        self.policy = policy or BinanceLivePolicy()
        self._client = client
        self._owns_client = client is None
        self._time_offset_ms = 0

    @property
    def base_url(self) -> str:
        return self.policy.testnet_url if self.policy.use_testnet else self.policy.base_url

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.policy.timeout_seconds)

    async def stop(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
        self._client = None

    async def ping(self) -> bool:
        client = self._require_client()
        response = await client.get(f"{self.base_url}/fapi/v1/ping")
        return response.status_code == 200

    async def sync_time(self) -> tuple[bool, int | None]:
        client = self._require_client()
        started = int(time.time() * 1000)
        response = await client.get(f"{self.base_url}/fapi/v1/time")
        ended = int(time.time() * 1000)
        if response.status_code != 200:
            return False, None
        server_time = int(response.json()["serverTime"])
        midpoint = (started + ended) // 2
        self._time_offset_ms = server_time - midpoint
        return (
            abs(self._time_offset_ms) <= self.policy.maximum_time_drift_ms,
            self._time_offset_ms,
        )

    async def account_snapshot(self) -> dict[str, Any]:
        if not self.credentials.configured:
            raise RuntimeError("Binance credentials are not configured")
        return await self._signed_get("/fapi/v2/account", {})

    async def readiness(self) -> BinanceReadinessReport:
        blockers: list[str] = []
        credentials_configured = self.credentials.configured
        if not credentials_configured:
            blockers.append("CREDENTIALS_NOT_CONFIGURED")

        try:
            public_ping_ok = await self.ping()
        except Exception:
            public_ping_ok = False
        if not public_ping_ok:
            blockers.append("PUBLIC_PING_FAILED")

        try:
            time_sync_ok, drift = await self.sync_time()
        except Exception:
            time_sync_ok, drift = False, None
        if not time_sync_ok:
            blockers.append("TIME_SYNC_FAILED")

        signed_account_access_ok = False
        if credentials_configured and public_ping_ok:
            try:
                await self.account_snapshot()
                signed_account_access_ok = True
            except Exception:
                blockers.append("SIGNED_ACCOUNT_ACCESS_FAILED")
        else:
            blockers.append("SIGNED_ACCOUNT_ACCESS_NOT_ATTEMPTED")

        status = "READY_FOR_TESTNET_VALIDATION" if not blockers else "NOT_READY"
        return BinanceReadinessReport(
            status=status,
            credentials_configured=credentials_configured,
            public_ping_ok=public_ping_ok,
            time_sync_ok=time_sync_ok,
            time_drift_ms=drift,
            signed_account_access_ok=signed_account_access_ok,
            testnet=self.policy.use_testnet,
            blockers=tuple(dict.fromkeys(blockers)),
            live_order_permission=False,
        )

    async def get_testnet_order(
        self,
        *,
        symbol: str,
        client_order_id: str | None = None,
        exchange_order_id: str | None = None,
    ) -> dict[str, Any]:
        if not self.policy.use_testnet:
            raise RuntimeError('Order query is restricted to TESTNET')
        params: dict[str, Any] = {'symbol': symbol}
        if client_order_id:
            params['origClientOrderId'] = client_order_id
        elif exchange_order_id:
            params['orderId'] = exchange_order_id
        else:
            raise ValueError('order identifier is required')
        return await self._signed_get('/fapi/v1/order', params)

    async def cancel_testnet_order(
        self,
        *,
        symbol: str,
        client_order_id: str | None = None,
        exchange_order_id: str | None = None,
    ) -> dict[str, Any]:
        if not self.policy.use_testnet:
            raise RuntimeError('Order cancel is restricted to TESTNET')
        params: dict[str, Any] = {'symbol': symbol}
        if client_order_id:
            params['origClientOrderId'] = client_order_id
        elif exchange_order_id:
            params['orderId'] = exchange_order_id
        else:
            raise ValueError('order identifier is required')
        return await self._signed_delete('/fapi/v1/order', params)

    async def _signed_delete(
        self,
        path: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        client = self._require_client()
        timestamp = int(time.time() * 1000) + self._time_offset_ms
        payload = {
            **params,
            'timestamp': timestamp,
            'recvWindow': self.policy.recv_window_ms,
        }
        query = urlencode(payload)
        signature = hmac.new(
            self.credentials.api_secret.encode('utf-8'),
            query.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        headers = {'X-MBX-APIKEY': self.credentials.api_key}
        response = await client.delete(
            f'{self.base_url}{path}?{query}&signature={signature}',
            headers=headers,
        )
        response.raise_for_status()
        return dict(response.json())

    async def create_testnet_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None,
        reduce_only: bool,
        client_order_id: str,
    ) -> dict[str, Any]:
        if not self.policy.use_testnet:
            raise RuntimeError('Order creation is restricted to TESTNET')
        if not self.credentials.configured:
            raise RuntimeError('Binance credentials are not configured')
        params: dict[str, Any] = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
            'reduceOnly': 'true' if reduce_only else 'false',
            'newClientOrderId': client_order_id,
        }
        if price is not None:
            params['price'] = price
            params['timeInForce'] = 'GTC'
        return await self._signed_post('/fapi/v1/order', params)

    async def _signed_post(
        self,
        path: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        client = self._require_client()
        timestamp = int(time.time() * 1000) + self._time_offset_ms
        payload = {
            **params,
            'timestamp': timestamp,
            'recvWindow': self.policy.recv_window_ms,
        }
        query = urlencode(payload)
        signature = hmac.new(
            self.credentials.api_secret.encode('utf-8'),
            query.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        headers = {'X-MBX-APIKEY': self.credentials.api_key}
        response = await client.post(
            f'{self.base_url}{path}?{query}&signature={signature}',
            headers=headers,
        )
        response.raise_for_status()
        return dict(response.json())

    async def _signed_get(
        self,
        path: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        client = self._require_client()
        timestamp = int(time.time() * 1000) + self._time_offset_ms
        payload = {
            **params,
            "timestamp": timestamp,
            "recvWindow": self.policy.recv_window_ms,
        }
        query = urlencode(payload)
        signature = hmac.new(
            self.credentials.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers = {"X-MBX-APIKEY": self.credentials.api_key}
        response = await client.get(
            f"{self.base_url}{path}?{query}&signature={signature}",
            headers=headers,
        )
        response.raise_for_status()
        return dict(response.json())

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Connector is not started")
        return self._client
