import csv
import io
import zipfile
from pathlib import Path

from nexor_x.laboratory.historical_bridge import HistoricalDatasetBridge
from nexor_x.laboratory.legacy_results_adapter import LegacyLaboratoryResultsAdapter


def write_archive(path: Path, timestamps: list[int]) -> None:
    content = io.StringIO()
    writer = csv.writer(content)
    for timestamp in timestamps:
        writer.writerow([timestamp, 100, 102, 99, 101, 10, timestamp+299999])
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(path.with_suffix(".csv").name, content.getvalue())


def test_audits_nested_binance_monthly_archives(tmp_path: Path) -> None:
    archive = tmp_path / "BTCUSDT" / "BTCUSDT-5m-2026-01.zip"
    write_archive(archive, [1_767_225_600_000, 1_767_225_900_000, 1_767_226_200_000])
    report = HistoricalDatasetBridge().audit(tmp_path, workers=2)
    assert report["archive_count"] == 1
    assert report["symbol_count"] == 1
    assert report["total_rows"] == 3
    assert report["status_counts"] == {"USABLE": 1}
    assert report["coverage_by_symbol"]["BTCUSDT"]["rows"] == 3
    assert report["replay_requirements"]["resample_15m"] is True
    assert report["final_replay_readiness"]["legacy_engine_is_final_nexor_x"] is False
    assert report["final_replay_readiness"]["exact_final_strategy_replay_claim_allowed"] is False
    assert report["live_execution_allowed"] is False


def test_detects_gaps_duplicates_and_invalid_ohlcv(tmp_path: Path) -> None:
    archive = tmp_path / "ETHUSDT" / "ETHUSDT-5m-2026-01.zip"
    content = (
        "1767225600000,100,102,99,101,10\n"
        "1767225600000,100,102,99,101,10\n"
        "1767226500000,100,98,99,101,10\n"
    )
    archive.parent.mkdir(parents=True)
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("ETHUSDT-5m-2026-01.csv", content)
    item = HistoricalDatasetBridge().audit_archive(archive)
    assert item.status == "INVALID"
    assert item.duplicate_timestamps == 1
    assert item.non_monotonic_timestamps == 1
    assert item.missing_intervals == 2
    assert item.invalid_ohlcv_rows >= 1


def test_legacy_adapter_marks_results_as_diagnostic_only() -> None:
    rows = LegacyLaboratoryResultsAdapter().adapt([{
        "position_uid": "BTC|2026-01|1", "dataset_symbol": "BTCUSDT",
        "net_pnl_usdt": 4, "gross_pnl_usdt": 5, "estimated_cost_usdt": 1,
        "initial_risk_usdt": 2, "equity_at_open_usdt": 100,
        "mfe_r": 3, "mae_r": -0.5, "score": 90,
        "final_reason": "BACKTEST_TP2",
    }])
    trade = rows[0]
    assert trade["net_pnl"] == 4
    assert trade["realized_r"] == 2
    assert trade["risk_pct"] == 2
    assert trade["source_profile"] == "LEGACY_7_3_15_58_NOT_FINAL_NEXOR_X"
    assert trade["diagnostic_only"] is True
