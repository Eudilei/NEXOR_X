from datetime import UTC, datetime, timedelta

from nexor_x.validation.final_campaign import (
    FinalValidationCampaignController,
    FinalValidationCampaignPolicy,
)


def passed_audit():
    return {
        "status": "PASS",
        "passed": True,
        "failed_checks": [],
    }


def failed_audit():
    return {
        "status": "FAIL",
        "passed": False,
        "failed_checks": ["entry_and_summary_agree"],
    }


def test_first_pass_is_recorded(tmp_path) -> None:
    c = FinalValidationCampaignController(
        state_path=tmp_path / "campaign.json"
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)

    r = c.record(audit=passed_audit(), now=t0)

    assert r["sample_counted"] is True
    assert r["valid_passes"] == 1
    assert r["consecutive_passes"] == 1


def test_polling_too_fast_does_not_count(tmp_path) -> None:
    c = FinalValidationCampaignController(
        state_path=tmp_path / "campaign.json"
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)

    c.record(audit=passed_audit(), now=t0)
    r = c.record(
        audit=passed_audit(),
        now=t0 + timedelta(minutes=5),
    )

    assert r["sample_counted"] is False
    assert r["valid_passes"] == 1


def test_failure_resets_consecutive_passes(tmp_path) -> None:
    c = FinalValidationCampaignController(
        state_path=tmp_path / "campaign.json"
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)

    c.record(audit=passed_audit(), now=t0)
    r = c.record(
        audit=failed_audit(),
        now=t0 + timedelta(minutes=30),
    )

    assert r["failures"] == 1
    assert r["consecutive_passes"] == 0
    assert r["last_failed_checks"] == [
        "entry_and_summary_agree"
    ]


def test_campaign_requires_passes_and_time(tmp_path) -> None:
    policy = FinalValidationCampaignPolicy(
        required_passes=2,
        minimum_interval_seconds=30 * 60,
        minimum_campaign_seconds=60 * 60,
    )
    c = FinalValidationCampaignController(
        state_path=tmp_path / "campaign.json",
        policy=policy,
    )
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)

    c.record(audit=passed_audit(), now=t0)
    r2 = c.record(
        audit=passed_audit(),
        now=t0 + timedelta(minutes=30),
    )
    assert r2["completed"] is False

    r3 = c.status(now=t0 + timedelta(minutes=60))
    assert r3["completed"] is True
    assert r3["status"] == "COMPLETE"


def test_state_survives_restart(tmp_path) -> None:
    path = tmp_path / "campaign.json"
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)

    c1 = FinalValidationCampaignController(state_path=path)
    c1.record(audit=passed_audit(), now=t0)

    c2 = FinalValidationCampaignController(state_path=path)
    r = c2.status(now=t0 + timedelta(minutes=10))

    assert r["valid_passes"] == 1
    assert r["live_allowed"] is False
