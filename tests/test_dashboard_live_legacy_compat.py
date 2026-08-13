from nexor_x.dashboard.command_center import COMMAND_CENTER_V2


def test_dashboard_keeps_legacy_live_blocked_literal_for_regression() -> None:
    assert "LIVE BLOQUEADO" in COMMAND_CENTER_V2
    assert "OPERAÇÃO REAL BLOQUEADA" in COMMAND_CENTER_V2
    assert "garantia de lucro" in COMMAND_CENTER_V2
