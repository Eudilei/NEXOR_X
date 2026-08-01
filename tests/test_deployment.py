from pathlib import Path

from nexor_x.config import _environment_overrides


def test_render_blueprint_exists_and_keeps_live_blocked() -> None:
    text = Path("render.yaml").read_text(encoding="utf-8")
    assert "healthCheckPath: /health" in text
    assert "NEXOR_MODE" in text and "PAPER" in text
    assert "ALLOW_LIVE_MODE" in text and '"false"' in text
    assert "sync: false" in text


def test_provider_port_overrides_yaml(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "10000")
    assert _environment_overrides()["nexor_port"] == "10000"
