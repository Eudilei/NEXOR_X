from nexor_x.config import Settings


def test_scanner_settings_have_safe_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.scanner_enabled is True
    assert settings.scanner_symbol_list[:2] == ("BTCUSDT", "ETHUSDT")
    assert settings.scanner_interval_seconds >= 15
    assert settings.scanner_concurrency >= 1
