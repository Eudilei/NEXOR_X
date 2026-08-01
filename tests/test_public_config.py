from nexor_x.config import Settings


def test_public_config_masks_secrets() -> None:
    settings = Settings(
        binance_api_key="key",
        binance_api_secret="secret",
        telegram_bot_token="token",
    )
    public = settings.public_dict()
    assert public["binance_api_key"] == "***"
    assert public["binance_api_secret"] == "***"
    assert public["telegram_bot_token"] == "***"
