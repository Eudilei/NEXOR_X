from types import SimpleNamespace

import pytest

from nexor_x.runtime import RuntimeProcessManager


@pytest.mark.asyncio
async def test_status_contains_local_panel_url() -> None:
    settings = SimpleNamespace(
        nexor_host="0.0.0.0",
        nexor_port=8809,
    )
    manager = RuntimeProcessManager(settings)
    status = await manager.status()
    assert status["local_panel_url"] == "http://127.0.0.1:8809"
    assert status["public_panel_url"] is None
    assert status["live_enabled"] is False


def test_cloudflare_url_pattern() -> None:
    text = (
        "INF Your quick Tunnel has been created! "
        "Visit it at https://abc-def.trycloudflare.com"
    )
    match = RuntimeProcessManager._TUNNEL_URL.search(text)
    assert match is not None
    assert match.group(0) == "https://abc-def.trycloudflare.com"


@pytest.mark.asyncio
async def test_missing_optional_binaries_do_not_crash(monkeypatch) -> None:
    settings = SimpleNamespace(
        ollama_autostart=True,
        ollama_command="missing-ollama",
        cloudflared_enabled=True,
        cloudflared_command="missing-cloudflared",
        nexor_host="127.0.0.1",
        nexor_port=8809,
    )
    monkeypatch.setattr("nexor_x.runtime.service.shutil.which", lambda _: None)

    manager = RuntimeProcessManager(settings)
    await manager.start_ollama()
    await manager.start_cloudflared()
    status = await manager.status()

    assert status["ollama"]["running"] is False
    assert status["cloudflared"]["running"] is False
    assert "não encontrado" in status["ollama"]["details"]
