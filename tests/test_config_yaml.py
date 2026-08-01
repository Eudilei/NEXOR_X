from pathlib import Path

from nexor_x.config import _yaml_values


def test_yaml_values_reads_nested_configuration(tmp_path: Path) -> None:
    path = tmp_path / "settings.yaml"
    path.write_text(
        "system:\n  mode: PAPER\n  port: 8811\n"
        "binance:\n  testnet: true\n"
        "ollama:\n  model: qwen2.5:3b\n",
        encoding="utf-8",
    )
    values = _yaml_values(path)
    assert values["nexor_port"] == 8811
    assert values["binance_testnet"] is True
    assert values["ollama_model"] == "qwen2.5:3b"
