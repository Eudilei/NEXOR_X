import pytest

from nexor_x.operations.entry_admission import EntryAdmissionController


def test_normal_allows_new_entry() -> None:
    result = EntryAdmissionController().evaluate(
        degradation={"state": "NORMAL", "new_entries_allowed": True},
        action="PAPER_OPEN",
    )
    assert result["allowed"] is True
    assert result["reason"] == "ALLOWED"
    assert result["live_allowed"] is False


def test_caution_allows_but_marks_caution() -> None:
    result = EntryAdmissionController().evaluate(
        degradation={
            "state": "CAUTION",
            "new_entries_allowed": True,
            "caution_reasons": ["profit_factor_weak"],
        },
        action="PAPER_OPEN",
    )
    assert result["allowed"] is True
    assert result["reason"] == "ALLOWED_WITH_CAUTION"


def test_blocked_rejects_new_entry() -> None:
    result = EntryAdmissionController().evaluate(
        degradation={
            "state": "BLOCKED",
            "new_entries_allowed": False,
            "hard_reasons": ["drawdown_limit_reached"],
        },
        action="TESTNET_CREATE",
    )
    assert result["allowed"] is False


def test_reduce_only_is_never_blocked_by_degradation() -> None:
    result = EntryAdmissionController().evaluate(
        degradation={
            "state": "BLOCKED",
            "new_entries_allowed": False,
            "hard_reasons": ["loss_streak_critical"],
        },
        action="TESTNET_CREATE",
        reduce_only=True,
    )
    assert result["allowed"] is True
    assert result["reason"] == "PROTECTIVE_REDUCE_ONLY"
    assert result["manage_existing_positions"] is True


def test_require_raises_for_blocked_new_entry() -> None:
    with pytest.raises(RuntimeError, match="performance degradation"):
        EntryAdmissionController().require(
            degradation={
                "state": "BLOCKED",
                "new_entries_allowed": False,
                "hard_reasons": ["profit_factor_below_1"],
            },
            action="PAPER_OPEN",
        )


def test_require_returns_for_reduce_only() -> None:
    result = EntryAdmissionController().require(
        degradation={"state": "BLOCKED", "new_entries_allowed": False},
        action="TESTNET_CREATE",
        reduce_only=True,
    )
    assert result["allowed"] is True
