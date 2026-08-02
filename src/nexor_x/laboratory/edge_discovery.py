from __future__ import annotations

import math
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterable

from nexor_x.infrastructure.database import DatabaseService
from .models import OutcomeObservation


def _edge_bucket(value: float, width: float = 0.20) -> str:
    clipped = max(-1.0, min(1.0, value))
    start = max(-1.0, math.floor((clipped + 1.0) / width) * width - 1.0)
    end = min(1.0, start + width)
    return f"{start:.2f}:{end:.2f}"


def _profit_factor(items: list[OutcomeObservation]) -> float | None:
    profit = sum(x.realized_r for x in items if x.realized_r > 0)
    loss = abs(sum(x.realized_r for x in items if x.realized_r < 0))
    return profit / loss if loss > 0 else (float("inf") if profit > 0 else None)


def _wilson_lower(wins: int, total: int, z: float = 1.96) -> float:
    if total <= 0:
        return 0.0
    p = wins / total
    denominator = 1 + z * z / total
    center = p + z * z / (2 * total)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return max(0.0, (center - margin) / denominator)


def _sign_test_p_value(wins: int, total: int) -> float:
    """Exact one-sided binomial p-value for win rate > 50%."""
    if total <= 0:
        return 1.0
    return min(1.0, sum(math.comb(total, k) for k in range(wins, total + 1)) / (2**total))


def _bh_q_values(p_values: list[float]) -> list[float]:
    if not p_values:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    m = len(indexed)
    adjusted = [1.0] * m
    running = 1.0
    for rank in range(m, 0, -1):
        original_index, p = indexed[rank - 1]
        running = min(running, p * m / rank)
        adjusted[original_index] = min(1.0, running)
    return adjusted


@dataclass(frozen=True, slots=True)
class EdgeCandidate:
    scope: str
    symbol: str | None
    decision: str
    regime: str
    edge_bucket: str
    samples: int
    wins: int
    win_rate: float
    win_rate_lower_95: float
    expected_r: float
    profit_factor: float | None
    first_half_expected_r: float
    second_half_expected_r: float
    stable: bool
    p_value: float
    q_value: float
    discovery_score: float
    status: str
    rejection_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope, "symbol": self.symbol, "decision": self.decision,
            "regime": self.regime, "edge_bucket": self.edge_bucket,
            "samples": self.samples, "wins": self.wins, "win_rate": self.win_rate,
            "win_rate_lower_95": self.win_rate_lower_95, "expected_r": self.expected_r,
            "profit_factor": self.profit_factor, "first_half_expected_r": self.first_half_expected_r,
            "second_half_expected_r": self.second_half_expected_r, "stable": self.stable,
            "p_value": self.p_value, "q_value": self.q_value,
            "discovery_score": self.discovery_score, "status": self.status,
            "rejection_reasons": list(self.rejection_reasons),
        }


class EdgeDiscoveryEngine:
    """Discovers recurring profitable contexts without authorizing execution.

    Multiple-testing correction and chronological stability are mandatory. A candidate is a
    research hypothesis, not permission to trade and not a promise of future profitability.
    """

    def __init__(
        self,
        database: DatabaseService,
        minimum_samples: int = 30,
        minimum_expected_r: float = 0.05,
        minimum_profit_factor: float = 1.10,
        maximum_fdr: float = 0.10,
    ) -> None:
        self.database = database
        self.minimum_samples = minimum_samples
        self.minimum_expected_r = minimum_expected_r
        self.minimum_profit_factor = minimum_profit_factor
        self.maximum_fdr = maximum_fdr

    def analyze(self, observations: Iterable[OutcomeObservation]) -> list[EdgeCandidate]:
        ordered = sorted(observations, key=lambda x: x.closed_at)
        groups: dict[tuple[str, str | None, str, str, str], list[OutcomeObservation]] = defaultdict(list)
        for item in ordered:
            bucket = _edge_bucket(item.raw_edge)
            groups[("GLOBAL", None, item.decision, item.regime, bucket)].append(item)
            groups[("SYMBOL", item.symbol, item.decision, item.regime, bucket)].append(item)

        provisional: list[dict[str, Any]] = []
        for (scope, symbol, decision, regime, bucket), items in groups.items():
            if len(items) < self.minimum_samples:
                continue
            midpoint = len(items) // 2
            first, second = items[:midpoint], items[midpoint:]
            expected = sum(x.realized_r for x in items) / len(items)
            first_ev = sum(x.realized_r for x in first) / len(first) if first else 0.0
            second_ev = sum(x.realized_r for x in second) / len(second) if second else 0.0
            wins = sum(1 for x in items if x.realized_r > 0)
            provisional.append({
                "scope": scope, "symbol": symbol, "decision": decision, "regime": regime,
                "edge_bucket": bucket, "items": items, "samples": len(items), "wins": wins,
                "win_rate": wins / len(items), "lower": _wilson_lower(wins, len(items)),
                "expected": expected, "pf": _profit_factor(items), "first_ev": first_ev,
                "second_ev": second_ev, "stable": first_ev > 0 and second_ev > 0,
                "p": _sign_test_p_value(wins, len(items)),
            })

        q_values = _bh_q_values([x["p"] for x in provisional])
        candidates: list[EdgeCandidate] = []
        for data, q in zip(provisional, q_values, strict=True):
            reasons: list[str] = []
            if data["expected"] < self.minimum_expected_r:
                reasons.append("expectativa abaixo do minimo")
            pf = data["pf"]
            if pf is None or pf < self.minimum_profit_factor:
                reasons.append("profit factor abaixo do minimo")
            if not data["stable"]:
                reasons.append("instavel entre metades temporais")
            if q > self.maximum_fdr:
                reasons.append("nao significativo apos controle de multiplos testes")
            status = "DISCOVERED" if not reasons else "REJECTED"
            finite_pf = 10.0 if pf == float("inf") else (pf or 0.0)
            score = max(0.0, data["expected"]) * data["lower"] * min(3.0, finite_pf) * math.log1p(data["samples"])
            candidates.append(EdgeCandidate(
                scope=data["scope"], symbol=data["symbol"], decision=data["decision"],
                regime=data["regime"], edge_bucket=data["edge_bucket"], samples=data["samples"],
                wins=data["wins"], win_rate=round(data["win_rate"], 6),
                win_rate_lower_95=round(data["lower"], 6), expected_r=round(data["expected"], 6),
                profit_factor=(None if pf is None else (float("inf") if pf == float("inf") else round(pf, 6))),
                first_half_expected_r=round(data["first_ev"], 6),
                second_half_expected_r=round(data["second_ev"], 6), stable=data["stable"],
                p_value=round(data["p"], 8), q_value=round(q, 8),
                discovery_score=round(score, 6), status=status,
                rejection_reasons=tuple(reasons),
            ))
        return sorted(candidates, key=lambda x: (x.status == "DISCOVERED", x.discovery_score), reverse=True)

    async def discover(self, observations: list[OutcomeObservation]) -> dict[str, Any]:
        candidates = self.analyze(observations)
        run_id = uuid.uuid4().hex
        generated_at = datetime.now(UTC).isoformat()
        await self.database.execute(
            "INSERT INTO edge_discovery_runs(run_id, generated_at, observation_count, candidate_count, discovered_count) VALUES(?,?,?,?,?)",
            (run_id, generated_at, len(observations), len(candidates), sum(x.status == "DISCOVERED" for x in candidates)),
        )
        for item in candidates:
            await self.database.execute(
                """INSERT INTO edge_candidates(run_id, scope, symbol, decision, regime, edge_bucket,
                samples, win_rate, win_rate_lower_95, expected_r, profit_factor, first_half_expected_r,
                second_half_expected_r, stable, p_value, q_value, discovery_score, status, reasons_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, item.scope, item.symbol, item.decision, item.regime, item.edge_bucket,
                 item.samples, item.win_rate, item.win_rate_lower_95, item.expected_r,
                 None if item.profit_factor == float("inf") else item.profit_factor,
                 item.first_half_expected_r, item.second_half_expected_r, int(item.stable),
                 item.p_value, item.q_value, item.discovery_score, item.status,
                 __import__("json").dumps(item.rejection_reasons)),
            )
        return {
            "run_id": run_id, "generated_at": generated_at,
            "observation_count": len(observations), "candidate_count": len(candidates),
            "discovered_count": sum(x.status == "DISCOVERED" for x in candidates),
            "candidates": [x.to_dict() for x in candidates],
            "execution_allowed": False, "live_certified": False,
            "warning": "Edges descobertos sao hipoteses de pesquisa e exigem validacao fora da amostra.",
        }

    async def latest(self) -> dict[str, Any]:
        rows = await self.database.fetchall(
            "SELECT run_id, generated_at, observation_count, candidate_count, discovered_count FROM edge_discovery_runs ORDER BY generated_at DESC LIMIT 1"
        )
        if not rows:
            return {"last_run": None, "execution_allowed": False, "live_certified": False}
        run = rows[0]
        candidates = await self.database.fetchall(
            """SELECT scope, symbol, decision, regime, edge_bucket, samples, win_rate,
            win_rate_lower_95, expected_r, profit_factor, first_half_expected_r,
            second_half_expected_r, stable, p_value, q_value, discovery_score, status, reasons_json
            FROM edge_candidates WHERE run_id=? ORDER BY CASE status WHEN 'DISCOVERED' THEN 0 ELSE 1 END, discovery_score DESC""",
            (run[0],),
        )
        import json
        return {"last_run": {
            "run_id": run[0], "generated_at": run[1], "observation_count": run[2],
            "candidate_count": run[3], "discovered_count": run[4],
            "candidates": [{
                "scope": r[0], "symbol": r[1], "decision": r[2], "regime": r[3],
                "edge_bucket": r[4], "samples": r[5], "win_rate": r[6],
                "win_rate_lower_95": r[7], "expected_r": r[8], "profit_factor": r[9],
                "first_half_expected_r": r[10], "second_half_expected_r": r[11],
                "stable": bool(r[12]), "p_value": r[13], "q_value": r[14],
                "discovery_score": r[15], "status": r[16], "rejection_reasons": json.loads(r[17]),
            } for r in candidates]}, "execution_allowed": False, "live_certified": False}
