from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping


class LegacyLaboratoryResultsAdapter:
    """Maps 7.3.15.58 positions to diagnostic records, never to final proof."""

    def adapt(self, rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [self._adapt_one(dict(row), index) for index, row in enumerate(rows)]

    def from_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.is_file():
            raise ValueError(f"positions.jsonl nao encontrado: {path}")
        rows = []
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"JSON invalido na linha {line_number}") from exc
        return self.adapt(rows)

    def _adapt_one(self, row: dict[str, Any], index: int) -> dict[str, Any]:
        net = float(row.get("net_pnl_usdt") or 0.0)
        risk = abs(float(row.get("initial_risk_usdt") or 0.0))
        equity = abs(float(row.get("equity_at_open_usdt") or 0.0))
        return {
            "trade_id": str(row.get("position_uid") or row.get("plan_uid") or index),
            "symbol": str(row.get("dataset_symbol") or row.get("symbol") or "UNKNOWN"),
            "strategy_id": "LEGACY_COGNITIVE_7_3_15_58",
            "regime": str(row.get("regime") or "UNKNOWN"),
            "gross_pnl": float(row.get("gross_pnl_usdt") or net),
            "total_fees": float(row.get("estimated_cost_usdt") or 0.0),
            "net_pnl": net,
            "realized_r": net/risk if risk else 0.0,
            "mfe_r": float(row.get("mfe_r") or 0.0),
            "mae_r": abs(float(row.get("mae_r") or 0.0)),
            "risk_pct": risk/equity*100 if equity else None,
            "raw_edge": self._edge(row),
            "exit_reason": str(row.get("final_reason") or row.get("reason") or "UNKNOWN"),
            "opened_at": row.get("opened_at"),
            "closed_at": row.get("closed_at"),
            "source_profile": "LEGACY_7_3_15_58_NOT_FINAL_NEXOR_X",
            "diagnostic_only": True,
        }

    @staticmethod
    def _edge(row: Mapping[str, Any]) -> float | None:
        score = row.get("score")
        if score is None:
            return None
        return max(-1.0, min(1.0, (float(score)-50.0)/50.0))
