from pathlib import Path


def test_patch_script_exists() -> None:
    assert Path("tools/apply_sprint18.py").exists()
