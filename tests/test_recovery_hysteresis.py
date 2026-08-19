from datetime import UTC, datetime, timedelta

from nexor_x.operations.recovery_hysteresis import (
    RecoveryHysteresisController,
    RecoveryHysteresisPolicy,
)


def blocked() -> dict[str, object]:
    return {
        "state": "BLOCKED",
        "new_entries_allowed": False,
        "hard_reasons": ["profit_factor_below_1"],
    }


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
        "hard_reasons": [],
        "caution_reasons": ["evidence_not_certified"],
        "recovery_reasons": ["shadow_recovery_confirmed"],
    }


def test_block_is_latched_and_persisted(tmp_path) -> None:
    state_file = tmp_path / "recovery.json"
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)

    first = RecoveryHysteresisController(state_path=state_file)
    report = first.evaluate(degradation=blocked(), now=t0)

    assert report["latched"] is True
    assert report["effective_state"] == "BLOCKED"
    assert state_file.exists()

    second = RecoveryHysteresisController(state_path=state_file)
    restored = second.evaluate(
        degradation=normal(),
        now=t0 + timedelta(minutes=1),
    )
    assert restored["latched"] is True
    assert restored["new_entries_allowed"] is False


def test_three_spaced_normal_checks_and_cooldown_release(tmp_path) -> None:
    policy = RecoveryHysteresisPolicy(
        cooldown_seconds=15 * 60,
        required_healthy_checks=3,
        min_healthy_check_interval_seconds=5 * 60,
    )
    guard = RecoveryHysteresisController(
        state_path=tmp_path / "recovery.json",
        policy=policy,
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)

    guard.evaluate(degradation=blocked(), now=t0)
    r1 = guard.evaluate(degradation=normal(), now=t0 + timedelta(minutes=5))
    r2 = guard.evaluate(degradation=normal(), now=t0 + timedelta(minutes=10))
    r3 = guard.evaluate(degradation=normal(), now=t0 + timedelta(minutes=15))

    assert r1["healthy_checks"] == 1
    assert r2["healthy_checks"] == 2
    assert r3["latched"] is False
    assert r3["transition"] == "RECOVERED"
    assert r3["new_entries_allowed"] is True


def test_fast_polling_does_not_fake_healthy_checks(tmp_path) -> None:
    guard = RecoveryHysteresisController(
        state_path=tmp_path / "recovery.json"
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)

    guard.evaluate(degradation=blocked(), now=t0)
    first = guard.evaluate(
        degradation=normal(),
        now=t0 + timedelta(minutes=5),
    )
    second = guard.evaluate(
        degradation=normal(),
        now=t0 + timedelta(minutes=6),
    )

    assert first["healthy_checks"] == 1
    assert second["healthy_checks"] == 1
    assert second["latched"] is True


def test_caution_resets_recovery_confirmations(tmp_path) -> None:
    guard = RecoveryHysteresisController(
        state_path=tmp_path / "recovery.json"
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)

    guard.evaluate(degradation=blocked(), now=t0)
    guard.evaluate(degradation=normal(), now=t0 + timedelta(minutes=5))
    report = guard.evaluate(
        degradation=caution(),
        now=t0 + timedelta(minutes=10),
    )

    assert report["latched"] is True
    assert report["healthy_checks"] == 0
    assert report["effective_state"] == "BLOCKED"


def test_new_blocked_state_resets_recovery_progress(tmp_path) -> None:
    guard = RecoveryHysteresisController(
        state_path=tmp_path / "recovery.json"
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)

    guard.evaluate(degradation=blocked(), now=t0)
    guard.evaluate(degradation=normal(), now=t0 + timedelta(minutes=5))
    report = guard.evaluate(
        degradation=blocked(),
        now=t0 + timedelta(minutes=10),
    )

    assert report["latched"] is True
    assert report["healthy_checks"] == 0
    assert report["new_entries_allowed"] is False


def test_shadow_recovery_caution_can_complete_hysteresis(tmp_path) -> None:
    guard = RecoveryHysteresisController(
        state_path=tmp_path / "recovery.json"
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    guard.evaluate(degradation=blocked(), now=t0)
    guard.evaluate(degradation=shadow_recovery_caution(), now=t0 + timedelta(minutes=5))
    guard.evaluate(degradation=shadow_recovery_caution(), now=t0 + timedelta(minutes=10))
    report = guard.evaluate(
        degradation=shadow_recovery_caution(), now=t0 + timedelta(minutes=15)
    )
    assert report["transition"] == "RECOVERED"
    assert report["new_entries_allowed"] is True
