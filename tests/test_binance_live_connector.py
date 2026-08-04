from __future__ import annotations

import hashlib
import hmac
from urllib.parse import urlencode

import httpx
import pytest

from nexor_x.exchange import (
    BinanceCredentials,
    BinanceLiveConnector,
    BinanceLivePolicy,
)


@pytest.mark.asyncio
async def test_readiness_without_credentials_is_blocked() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ping"):
            return httpx.Response(200, json={})
        if request.url.path.endswith("/time"):
            return httpx.Response(200, json={"serverTime": 1_700_000_000_000})
        return httpx.Response(401, json={"code": -2015})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = BinanceLiveConnector(
        BinanceCredentials("", ""),
        BinanceLivePolicy(use_testnet=True, maximum_time_drift_ms=10**15),
        client,
    )
    await connector.start()
    try:
        result = await connector.readiness()
        assert result.status == "NOT_READY"
        assert "CREDENTIALS_NOT_CONFIGURED" in result.blockers
        assert result.live_order_permission is False
    finally:
        await connector.stop()


@pytest.mark.asyncio
async def test_signed_account_access_can_pass_on_testnet() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ping"):
            return httpx.Response(200, json={})
        if request.url.path.endswith("/time"):
            return httpx.Response(200, json={"serverTime": 1_700_000_000_000})
        if request.url.path.endswith("/account"):
            assert request.headers["X-MBX-APIKEY"] == "key"
            assert "signature=" in request.url.query.decode()
            return httpx.Response(200, json={"assets": [], "positions": []})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = BinanceLiveConnector(
        BinanceCredentials("key", "secret"),
        BinanceLivePolicy(use_testnet=True, maximum_time_drift_ms=10**15),
        client,
    )
    await connector.start()
    try:
        result = await connector.readiness()
        assert result.signed_account_access_ok is True
        assert result.testnet is True
        assert result.live_order_permission is False
    finally:
        await connector.stop()
