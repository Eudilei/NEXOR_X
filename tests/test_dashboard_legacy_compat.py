from nexor_x.dashboard.command_center import COMMAND_CENTER_V2


def test_legacy_dashboard_labels_remain_for_regression_compatibility() -> None:
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
