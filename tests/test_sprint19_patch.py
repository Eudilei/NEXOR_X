from pathlib import Path


def test_apply_script_exists() -> None:
    assert Path("tools/apply_sprint19.py").exists()
