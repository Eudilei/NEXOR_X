import pytest
from pydantic import ValidationError
from nexor_x.config import Settings
from nexor_x.domain import OperatingMode

def test_paper_is_default() -> None:
    assert Settings(_env_file=None).nexor_mode is OperatingMode.PAPER

def test_live_is_blocked_without_gate() -> None:
    with pytest.raises(ValidationError):
        Settings(nexor_mode="LIVE", allow_live_mode=False, _env_file=None)

def test_live_requires_credentials() -> None:
    with pytest.raises(ValidationError):
        Settings(nexor_mode="LIVE", allow_live_mode=True, _env_file=None)
