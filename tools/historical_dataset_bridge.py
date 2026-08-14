from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from nexor_x.infrastructure.database import DatabaseService
from nexor_x.laboratory.backtest_diagnostics import BacktestDiagnosticEngine
from nexor_x.laboratory.historical_bridge import HistoricalDatasetBridge
from nexor_x.laboratory.legacy_results_adapter import LegacyLaboratoryResultsAdapter


def audit(args: argparse.Namespace) -> None:
    bridge = HistoricalDatasetBridge()
    report = bridge.audit(args.data, workers=args.workers)
    json_path, md_path = bridge.write_reports(report, args.output)
    print(json.dumps({
        "archives": report["archive_count"], "symbols": report["symbol_count"],
        "candles": report["total_rows"], "status": report["status_counts"],
        "json": str(json_path.resolve()), "markdown": str(md_path.resolve()),
    }, ensure_ascii=False, indent=2))


async def diagnose_legacy_async(args: argparse.Namespace) -> None:
    adapter = LegacyLaboratoryResultsAdapter()
    trades = adapter.from_jsonl(args.positions)
    database = DatabaseService(args.database)
    await database.start()
    try:
        report = await BacktestDiagnosticEngine(database).diagnose(trades)
    finally:
        await database.stop()
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "legacy_backtest_diagnostics.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "trades": report["summary"]["trade_count"],
        "net_pnl": report["summary"]["net_pnl"],
        "warning": "resultado antigo e diagnostico, nao validacao do NEXOR X final",
        "report": str(path.resolve()),
    }, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ponte historica do NEXOR X")
    commands = parser.add_subparsers(dest="command", required=True)
    audit_parser = commands.add_parser("audit", help="audita ZIPs Binance 5m")
    audit_parser.add_argument("--data", required=True, type=Path)
    audit_parser.add_argument("--output", type=Path, default=Path("reports/historical_dataset"))
    audit_parser.add_argument("--workers", type=int, default=4)
    audit_parser.set_defaults(handler=audit)
    legacy = commands.add_parser("diagnose-legacy", help="diagnostica positions.jsonl antigo")
    legacy.add_argument("--positions", required=True, type=Path)
    legacy.add_argument("--output", type=Path, default=Path("reports/historical_dataset"))
    legacy.add_argument("--database", type=Path, default=Path("data/nexor_x.db"))
    legacy.set_defaults(handler=lambda args: asyncio.run(diagnose_legacy_async(args)))
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
