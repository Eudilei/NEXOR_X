from nexor_x.dashboard import COMMAND_CENTER_V2


def test_dashboard_has_critical_sections() -> None:
    for label in (
        "Supervisor",
        "Recovery Guard",
        "Certificação CQO",
        "Portfólio PAPER",
        "Scanner",
        "Estratégias",
        "Alocação",
        "IA local",
    ):
        assert label in COMMAND_CENTER_V2


def test_dashboard_never_claims_live_enabled() -> None:
    assert "LIVE BLOQUEADO" in COMMAND_CENTER_V2
    assert "garantia de lucro" in COMMAND_CENTER_V2


def test_dashboard_uses_existing_api_contracts() -> None:
    for endpoint in (
        "/api/status",
        "/api/market/BTCUSDT",
        "/api/quant/BTCUSDT",
        "/api/probability/BTCUSDT",
        "/api/portfolio/status",
        "/api/scanner/status",
        "/api/strategies/status",
        "/api/allocation/status",
        "/api/recovery/status",
        "/api/supervisor/status",
        "/api/certification/status",
        "/api/ai/chat",
    ):
        assert endpoint in COMMAND_CENTER_V2
