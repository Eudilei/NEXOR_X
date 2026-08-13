from nexor_x.operations import LiveReadinessEvaluator


def _ready(**overrides):
    payload = dict(
        mode="PAPER",
        credentials={"binance_configured": True},
        recovery={"recovery_ok": True},
        supervisor={"testnet_allowed": True},
        integration={"testnet_ready": True},
        validation={"testnet_validation_ready": True},
        campaign={"testnet_allowed": True},
        cycle={"days_running": 30},
        runtime={"live_enabled": False},
    )
    payload.update(overrides)
    return LiveReadinessEvaluator().evaluate(**payload)


def test_live_is_always_blocked_even_when_candidate_ready() -> None:
    report = _ready()
    assert report["candidate_ready"] is True
    assert report["live_allowed"] is False
    assert report["live_certified"] is False


def test_missing_validation_creates_blockers() -> None:
    report = _ready(
        validation={"testnet_validation_ready": False},
        campaign={"testnet_allowed": False},
        cycle={},
    )
    assert report["candidate_ready"] is False
    assert "validation_testnet_ready" in report["blockers"]
    assert "campaign_allows_testnet" in report["blockers"]
    assert "validation_cycle_present" in report["blockers"]


def test_live_mode_is_never_accepted_as_safe_mode() -> None:
    report = _ready(mode="LIVE")
    assert report["checks"]["safe_mode"] is False
    assert report["live_allowed"] is False
