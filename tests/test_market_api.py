from datetime import UTC, datetime

from fastapi.testclient import TestClient

from nexor_x.api.app import create_app
from nexor_x.market.models import MarketSnapshot


class FakeSettings:
    nexor_mode = type("Mode", (), {"value": "PAPER"})()

    def public_dict(self):
        return {"nexor_mode": "PAPER"}


class FakeBinance:
    def diagnostics(self):
        return {"last_error": "", "cooldown_active": False}


class FakeOllama:
    async def chat(self, message, context):
        return "ok"


class FakeKernel:
    settings = FakeSettings()
    binance = FakeBinance()
    ollama = FakeOllama()

    async def status(self):
        return {"state": "ONLINE", "services": [], "mode": "PAPER"}

    async def market_state(self, symbol):
        if symbol == "bad":
            raise ValueError("Simbolo invalido")
        snap = MarketSnapshot(
            symbol="BTCUSDT",
            price=1,
            open_price=1,
            high_price=1,
            low_price=1,
            volume=1,
            quote_volume=1,
            price_change_percent=0,
            fetched_at=datetime.now(UTC),
            source="test",
        )
        return {"symbol": "BTCUSDT", "regime": "RANGE", "snapshot": snap.to_dict()}

    async def sleep(self, seconds):
        return None


def test_market_endpoint():
    client = TestClient(create_app(FakeKernel()))
    response = client.get("/api/market/BTCUSDT")
    assert response.status_code == 200
    assert response.json()["regime"] == "RANGE"


def test_market_validation_error():
    client = TestClient(create_app(FakeKernel()))
    response = client.get("/api/market/bad")
    assert response.status_code == 422


def test_favicon_no_longer_404():
    client = TestClient(create_app(FakeKernel()))
    assert client.get("/favicon.ico").status_code == 204
