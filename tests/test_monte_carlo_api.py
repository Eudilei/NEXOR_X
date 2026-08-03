from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from nexor_x.api.app import create_app


class KernelStub:
    def __init__(self):
        self.settings = SimpleNamespace(admin_api_token="secret")

    async def monte_carlo_status(self):
        return {"status": "NOT_RUN", "live_certified": False}

    async def run_monte_carlo(self, **kwargs):
        return {"status": "INSUFFICIENT_DATA", "run_id": "x", "kwargs": kwargs}


def test_monte_carlo_status_is_public():
    client = TestClient(create_app(KernelStub()))
    assert client.get("/api/monte-carlo/status").status_code == 200


def test_monte_carlo_run_requires_admin_token():
    client = TestClient(create_app(KernelStub()))
    assert client.post("/api/monte-carlo/run", json={}).status_code == 401
    response = client.post(
        "/api/monte-carlo/run", json={"simulations": 100},
        headers={"X-NEXOR-ADMIN-TOKEN": "secret"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "INSUFFICIENT_DATA"
