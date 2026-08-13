from nexor_x.dashboard.command_center import COMMAND_CENTER_V2


def test_visible_dashboard_terms_are_in_portuguese() -> None:
    for term in (
        "Supervisor Operacional",
        "Proteção de Recuperação",
        "Cérebro Quantitativo",
        "Probabilidade Calibrada",
        "Portfólio em Simulação",
        "Varredura de Mercado",
        "Alocação de Capital",
        "OPERAÇÃO REAL BLOQUEADA",
    ):
        assert term in COMMAND_CENTER_V2


def test_internal_codes_have_portuguese_mapping() -> None:
    for code, translated in (
        ("PAPER_AND_TESTNET_READY", "SIMULAÇÃO E REDE DE TESTES PRONTAS"),
        ("RECOVERY_NOT_CLEAN", "RECONCILIAÇÃO PENDENTE"),
        ("LONG_BIAS", "VIÉS DE COMPRA"),
        ("SHORT_BIAS", "VIÉS DE VENDA"),
        ("NO_EDGE", "SEM VANTAGEM"),
    ):
        assert code in COMMAND_CENTER_V2
        assert translated in COMMAND_CENTER_V2


def test_live_is_still_blocked() -> None:
    assert "OPERAÇÃO REAL BLOQUEADA" in COMMAND_CENTER_V2
    assert "live_allowed" not in COMMAND_CENTER_V2 or "false" in COMMAND_CENTER_V2.lower()
