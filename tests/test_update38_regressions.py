from pathlib import Path


def test_auto_paper_keeps_legacy_and_current_portfolio_shapes() -> None:
    text = Path(
        "src/nexor_x/autopaper/service.py"
    ).read_text(encoding="utf-8")

    assert 'portfolio.get("open_positions")' in text
    assert 'portfolio.get("positions")' in text
    assert "isinstance(raw_open_positions, (list, tuple))" in text


def test_position_management_is_scheduled() -> None:
    text = Path("src/nexor_x/kernel.py").read_text(encoding="utf-8")

    assert "auto_position_management_cycle" in text
    assert "_scheduled_auto_position_management" in text
