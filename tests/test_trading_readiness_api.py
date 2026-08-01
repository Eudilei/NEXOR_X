from fastapi.testclient import TestClient

from nexor_x.api.app import create_app


class KernelStub:
    async def trading_readiness(self, symbol: str):
        return {"symbol": symbol, "decision": "BLOCKED", "allowed": False}


def test_trading_readiness_endpoint():
    app = create_app(KernelStub())
    client = TestClient(app)
    response = client.get('/api/trading/readiness/BTCUSDT')
    assert response.status_code == 200
    assert response.json()["decision"] == "BLOCKED"
