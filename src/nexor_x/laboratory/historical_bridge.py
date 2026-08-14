from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


ARCHIVE_PATTERN = re.compile(
    r"^(?P<symbol>[A-Z0-9]+USDT)-5m-(?P<month>\d{4}-\d{2})\.zip$",
    re.IGNORECASE,
)
INTERVAL_MS = 300_000


@dataclass(frozen=True, slots=True)
class ArchiveAudit:
    path: str
    symbol: str
    month: str
    size_bytes: int
    sha256: str
    status: str
    rows: int
    first_open_ms: int | None
    last_open_ms: int | None
    duplicate_timestamps: int
    non_monotonic_timestamps: int
    invalid_ohlcv_rows: int
    missing_intervals: int
    largest_gap_ms: int
    csv_member_count: int
    error: str | None


class HistoricalDatasetBridge:
    """Read-only auditor for Binance monthly 5m kline archives."""

    def discover(self, data_root: Path) -> list[Path]:
        root = data_root.expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"pasta historica nao encontrada: {root}")
        return sorted(
            path for path in root.rglob("*USDT-5m-*.zip")
            if path.is_file() and ARCHIVE_PATTERN.match(path.name)
        )

    def audit(self, data_root: Path, *, workers: int = 4) -> dict[str, Any]:
        archives = self.discover(data_root)
        if not archives:
            raise ValueError(f"nenhum arquivo *USDT-5m-AAAA-MM.zip em {data_root}")
        workers = max(1, min(int(workers), 16))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            rows = list(executor.map(self.audit_archive, archives))
        return self._report(data_root.expanduser().resolve(), rows)

    def audit_archive(self, path: Path) -> ArchiveAudit:
        match = ARCHIVE_PATTERN.match(path.name)
        symbol = match.group("symbol").upper() if match else "UNKNOWN"
        month = match.group("month") if match else "UNKNOWN"
        digest = hashlib.sha256()
        try:
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            with zipfile.ZipFile(path) as archive:
                csv_members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
                if len(csv_members) != 1:
                    raise ValueError(f"ZIP_CSV_COUNT:{len(csv_members)}")
                with archive.open(csv_members[0]) as raw:
                    text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
                    metrics = self._audit_csv(csv.reader(text))
            return ArchiveAudit(
                str(path), symbol, month, path.stat().st_size, digest.hexdigest(),
                "USABLE" if metrics["invalid"] == 0 and metrics["non_monotonic"] == 0 else "INVALID",
                metrics["rows"], metrics["first"], metrics["last"], metrics["duplicates"],
                metrics["non_monotonic"], metrics["invalid"], metrics["missing"],
                metrics["largest_gap"], 1, None,
            )
        except Exception as exc:
            return ArchiveAudit(
                str(path), symbol, month, path.stat().st_size if path.exists() else 0,
                digest.hexdigest(), "ERROR", 0, None, None, 0, 0, 0, 0, 0, 0,
                f"{type(exc).__name__}:{exc}",
            )

    def _audit_csv(self, reader: Iterable[list[str]]) -> dict[str, int | None]:
        count = duplicates = non_monotonic = invalid = missing = largest_gap = 0
        first: int | None = None
        previous: int | None = None
        seen: set[int] = set()
        for row in reader:
            if not row or not str(row[0]).strip().isdigit():
                continue
            try:
                timestamp = self._timestamp_ms(int(row[0]))
                open_, high, low, close, volume = (float(row[index]) for index in range(1, 6))
                valid = (
                    all(math.isfinite(value) for value in (open_, high, low, close, volume))
                    and min(open_, high, low, close) > 0 and volume >= 0
                    and high >= max(open_, low, close) and low <= min(open_, high, close)
                )
            except (IndexError, TypeError, ValueError, OverflowError):
                invalid += 1
                continue
            count += 1
            invalid += int(not valid)
            duplicates += int(timestamp in seen)
            seen.add(timestamp)
            first = timestamp if first is None else min(first, timestamp)
            if previous is not None:
                delta = timestamp - previous
                non_monotonic += int(delta <= 0)
                if delta > INTERVAL_MS:
                    largest_gap = max(largest_gap, delta)
                    if delta % INTERVAL_MS == 0:
                        missing += max(0, delta // INTERVAL_MS - 1)
                    else:
                        invalid += 1
            previous = timestamp
        return {
            "rows": count, "first": first, "last": previous,
            "duplicates": duplicates, "non_monotonic": non_monotonic,
            "invalid": invalid, "missing": missing, "largest_gap": largest_gap,
        }

    @staticmethod
    def _timestamp_ms(value: int) -> int:
        while value > 99_999_999_999_999:
            value //= 1000
        if value < 100_000_000_000:
            value *= 1000
        return value

    def _report(self, root: Path, audits: list[ArchiveAudit]) -> dict[str, Any]:
        by_symbol: dict[str, list[ArchiveAudit]] = defaultdict(list)
        for item in audits:
            by_symbol[item.symbol].append(item)
        coverage = {}
        for symbol, items in sorted(by_symbol.items()):
            valid = [item for item in items if item.status == "USABLE"]
            coverage[symbol] = {
                "archives": len(items), "usable_archives": len(valid),
                "rows": sum(item.rows for item in valid),
                "first_open_ms": min((item.first_open_ms for item in valid if item.first_open_ms), default=None),
                "last_open_ms": max((item.last_open_ms for item in valid if item.last_open_ms), default=None),
                "missing_intervals": sum(item.missing_intervals for item in valid),
                "largest_gap_ms": max((item.largest_gap_ms for item in valid), default=0),
            }
        statuses = Counter(item.status for item in audits)
        usable = statuses["USABLE"] > 0 and statuses["ERROR"] == 0 and statuses["INVALID"] == 0
        return {
            "schema": "nexor_x.historical_dataset_audit.v1",
            "generated_at": datetime.now(UTC).isoformat(),
            "data_root": str(root),
            "timeframe": "5m",
            "archive_count": len(audits),
            "symbol_count": len(by_symbol),
            "total_rows": sum(item.rows for item in audits),
            "status_counts": dict(statuses),
            "dataset_usable": usable,
            "coverage_by_symbol": coverage,
            "archives": [asdict(item) for item in audits],
            "replay_requirements": {
                "resample_15m": True,
                "derive_4h_context_from_5m": True,
                "strict_closed_candle_only": True,
                "next_bar_execution": True,
                "same_bar_ambiguity_policy_required": True,
            },
            "unavailable_historical_inputs": [
                "real_spread", "real_slippage", "order_book", "open_interest",
                "historical_funding_unless_separately_enriched",
            ],
            "simulation_assumptions_required": True,
            "final_replay_readiness": {
                "status": "DATA_READY_ENGINE_FIDELITY_PENDING" if usable else "DATA_NOT_READY",
                "data_reader_compatible": True,
                "legacy_engine_is_final_nexor_x": False,
                "exact_final_strategy_replay_claim_allowed": False,
                "required_next_authority": (
                    "shared_bar_strategy_engine_used_by_runtime_and_laboratory"
                ),
            },
            "live_execution_allowed": False,
        }

    @staticmethod
    def write_reports(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "historical_dataset_audit.json"
        md_path = output_dir / "historical_dataset_audit.md"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = [
            "# Auditoria da Base Histórica", "",
            f"- Arquivos: {report['archive_count']}",
            f"- Símbolos: {report['symbol_count']}",
            f"- Candles: {report['total_rows']}",
            f"- Estados: {report['status_counts']}",
            f"- Base utilizável integralmente: {report['dataset_usable']}", "",
            "## Limitações conhecidas", "",
        ]
        lines.extend(f"- {item}" for item in report["unavailable_historical_inputs"])
        lines.extend(["", "## Cobertura por símbolo", ""])
        for symbol, item in report["coverage_by_symbol"].items():
            lines.append(
                f"- {symbol}: {item['rows']} candles; {item['usable_archives']}/"
                f"{item['archives']} arquivos úteis; faltas={item['missing_intervals']}"
            )
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return json_path, md_path
