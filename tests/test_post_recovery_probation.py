from datetime import UTC, datetime, timedelta

from nexor_x.operations.post_recovery_probation import (
    PostRecoveryProbationController,
)


def normal() -> dict[str, object]:
    return {
        "state": "NORMAL",
        "new_entries_allowed": True,
        "hard_reasons": [],
        "caution_reasons": [],
    }


def caution() -> dict[str, object]:
    return {
        "state": "CAUTION",
        "new_entries_allowed": True,
        "caution_reasons": ["profit_factor_weak"],
    }


def shadow_recovery_caution() -> dict[str, object]:
    return {
        "state": "CAUTION",
        "new_entries_allowed": True,
        "caution_reasons": ["evidence_not_certified"],
        "recovery_reasons": ["shadow_recovery_confirmed"],
    }


def test_probation_starts_persisted(tmp_path) -> None:
    state_file = tmp_path / "probation.json"
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)

    first = PostRecoveryProbationController(state_path=state_file)
    first.start(now=t0)

    second = PostRecoveryProbationController(state_path=state_file)
    status = second.status(now=t0 + timedelta(minutes=5))

    assert status["active"] is True
    assert status["admitted_entries"] == 0
    assert state_file.exists()


def test_first_normal_entry_is_allowed_and_recorded(tmp_path) -> None:
    guard = PostRecoveryProbationController(
        state_path=tmp_path / "probation.json"
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    guard.start(now=t0)

    report = guard.admit(
        degradation=normal(),
        action="PAPER_OPEN",
        now=t0,
    )

    assert report["allowed"] is True
    assert report["admitted_entries"] == 1


def test_second_entry_before_15_minutes_is_blocked(tmp_path) -> None:
    guard = PostRecoveryProbationController(
        state_path=tmp_path / "probation.json"
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    guard.start(now=t0)
    guard.admit(degradation=normal(), action="PAPER_OPEN", now=t0)

    report = guard.evaluate(
        degradation=normal(),
        action="PAPER_OPEN",
        now=t0 + timedelta(minutes=10),
    )

    assert report["allowed"] is False
    assert report["block_reason"] == "probation_entry_interval_active"


def test_three_entries_are_maximum_during_probation(tmp_path) -> None:
    guard = PostRecoveryProbationController(
        state_path=tmp_path / "probation.json"
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    guard.start(now=t0)

    guard.admit(degradation=normal(), action="PAPER_OPEN", now=t0)
    guard.admit(
        degradation=normal(),
        action="PAPER_OPEN",
        now=t0 + timedelta(minutes=15),
    )
    third = guard.admit(
        degradation=normal(),
        action="PAPER_OPEN",
        now=t0 + timedelta(minutes=30),
    )
    fourth = guard.evaluate(
        degradation=normal(),
        action="PAPER_OPEN",
        now=t0 + timedelta(minutes=45),
    )

    assert third["admitted_entries"] == 3
    assert fourth["allowed"] is False
    assert fourth["block_reason"] == "probation_entry_limit_reached"


def test_caution_blocks_new_entries_during_probation(tmp_path) -> None:
    guard = PostRecoveryProbationController(
        state_path=tmp_path / "probation.json"
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    guard.start(now=t0)

    report = guard.evaluate(
        degradation=caution(),
        action="TESTNET_CREATE",
        now=t0 + timedelta(minutes=20),
    )

    assert report["allowed"] is False
    assert report["block_reason"] == "probation_requires_normal_state"


def test_reduce_only_is_always_allowed(tmp_path) -> None:
    guard = PostRecoveryProbationController(
        state_path=tmp_path / "probation.json"
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    guard.start(now=t0)

    report = guard.evaluate(
        degradation=caution(),
        action="TESTNET_CREATE",
        reduce_only=True,
        now=t0 + timedelta(minutes=1),
    )

    assert report["allowed"] is True
    assert report["reduce_only"] is True


def test_probation_finishes_after_one_hour_when_normal(tmp_path) -> None:
    guard = PostRecoveryProbationController(
        state_path=tmp_path / "probation.json"
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    guard.start(now=t0)

    report = guard.evaluate(
        degradation=normal(),
        action="PAPER_OPEN",
        now=t0 + timedelta(minutes=61),
    )

    assert report["active"] is False
    assert report["allowed"] is True


def test_shadow_recovery_caution_allows_reduced_probation_entry(tmp_path) -> None:
    guard = PostRecoveryProbationController(
        state_path=tmp_path / "probation.json"
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    guard.start(now=t0)
    report = guard.admit(
        degradation=shadow_recovery_caution(), action="PAPER_OPEN", now=t0
    )
    assert report["allowed"] is True
    assert report["admitted_entries"] == 1
