from types import SimpleNamespace

import pytest

from nexor_x.secrets import ExternalCredentialsStatusService


@pytest.mark.asyncio
async def test_reports_configuration_without_exposing_secrets() -> None:
    settings = SimpleNamespace(
        binance_api_key="abc",
        binance_api_secret="def",
        telegram_bot_token="ghi",
        telegram_chat_id="123",
    )
    result = await ExternalCredentialsStatusService(settings).status()

    assert result["binance"]["ready"] is True
    assert result["telegram"]["ready"] is True
    assert result["secrets_exposed"] is False
    assert result["live_enabled"] is False
    text = str(result)
    assert "abc" not in text
    assert "def" not in text
    assert "ghi" not in text


@pytest.mark.asyncio
async def test_missing_credentials_are_reported() -> None:
    settings = SimpleNamespace(
        binance_api_key="",
        binance_api_secret="",
        telegram_bot_token="",
        telegram_chat_id="",
    )
    result = await ExternalCredentialsStatusService(settings).status()

    assert result["binance"]["ready"] is False
    assert result["telegram"]["ready"] is False
