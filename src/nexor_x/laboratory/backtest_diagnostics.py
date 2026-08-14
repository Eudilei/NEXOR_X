from __future__ import annotations

import json
import math
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterable, Mapping

from nexor_x.infrastructure.database import DatabaseService


@dataclass(frozen=True, slots=True)
class DiagnosticPolicy:
    minimum_planned_rr: float = 1.5
    maximum_slippage_bps: float = 8.0
    maximum_risk_pct: float = 2.0
    maximum_fee_share_of_gross: float = 0.35
    minimum_edge: float = 0.10
    missed_profit_r: float = 0.75
    excessive_giveback_r: float = 1.0
    severe_mae_r: float = 0.80


class BacktestDiagnosticEngine:
    """Explains recorded backtest outcomes without inventing market causes."""

    def __init__(self, database: DatabaseService, policy: DiagnosticPolicy | None = None) -> None:
        self.database = database
        self.policy = policy or DiagnosticPolicy()

    async def diagnose(self, trades: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        records = [dict(item) for item in trades]
        if not records:
            raise ValueError("ao menos uma operacao de backtest e obrigatoria")
        if len(records) > 100_000:
            raise ValueError("limite de 100000 operacoes por diagnostico")

        diagnoses = [self._diagnose_trade(item, index) for index, item in enumerate(records)]
        summary = self._summarize(diagnoses)
        run_id = str(uuid.uuid4())
        generated_at = datetime.now(UTC).isoformat()
        result = {
            "run_id": run_id,
            "generated_at": generated_at,
            "status": "DIAGNOSED",
            "profile": "NEXOR_X_FINAL_NET_AFTER_FEES",
            "summary": summary,
            "trades": diagnoses,
            "limitations": [
                "Causas sao diagnosticos baseados nos campos registrados, nao prova causal.",
                "Campos ausentes reduzem a confianca e sao informados por operacao.",
                "Nenhuma configuracao e alterada automaticamente.",
            ],
            "execution_allowed": False,
            "live_certified": False,
        }
        await self.database.execute(
            """INSERT INTO backtest_diagnostic_runs
            (run_id, generated_at, trade_count, net_pnl, status, report_json)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                generated_at,
                summary["trade_count"],
                summary["net_pnl"],
                result["status"],
                json.dumps(result, ensure_ascii=False, sort_keys=True),
            ),
        )
        return result

    async def latest(self) -> dict[str, Any]:
        rows = await self.database.fetchall(
            "SELECT report_json FROM backtest_diagnostic_runs ORDER BY generated_at DESC LIMIT 1"
        )
        return json.loads(str(rows[0][0])) if rows else {"status": "NEVER_RUN"}

    def _diagnose_trade(self, trade: dict[str, Any], index: int) -> dict[str, Any]:
        gross = self._number(trade, "gross_pnl", "gross_profit", default=0.0)
        entry_fee = self._number(trade, "entry_fee", default=0.0)
        exit_fee = self._number(trade, "exit_fee", default=0.0)
        total_fees = self._number(trade, "total_fees", "fees", default=entry_fee + exit_fee)
        net = self._number(trade, "net_pnl", "pnl", "realized_pnl", default=gross-total_fees)
        realized_r = self._number(trade, "realized_r", default=0.0)
        mfe_r = self._optional_number(trade, "mfe_r", "maximum_favorable_excursion_r")
        mae_r = self._optional_number(trade, "mae_r", "maximum_adverse_excursion_r")
        causes: list[dict[str, Any]] = []
        missing = [
            name for name in ("strategy_id", "regime", "exit_reason", "realized_r")
            if trade.get(name) in (None, "")
        ]

        def add(code: str, severity: str, evidence: str, action: str) -> None:
            causes.append({
                "code": code, "severity": severity, "evidence": evidence,
                "suggested_test": action,
            })

        if gross > 0 >= net:
            add("COST_DRAG", "HIGH", f"bruto={gross:.8f}; taxas={total_fees:.8f}; liquido={net:.8f}",
                "comparar maker/taker, spread e frequencia sem remover custos")
        elif gross > 0 and total_fees / gross > self.policy.maximum_fee_share_of_gross:
            add("HIGH_FEE_SHARE", "MEDIUM", f"taxas consumiram {total_fees/gross:.1%} do bruto",
                "testar filtro de ganho minimo acima do custo total")

        slippage = self._optional_number(trade, "slippage_bps")
        if slippage is not None and abs(slippage) > self.policy.maximum_slippage_bps:
            add("EXCESSIVE_SLIPPAGE", "HIGH", f"slippage={slippage:.2f} bps",
                "segmentar por liquidez e horario; validar modelo de fill")

        planned_rr = self._optional_number(trade, "planned_rr", "risk_reward")
        if planned_rr is not None and planned_rr < self.policy.minimum_planned_rr:
            add("LOW_PLANNED_RR", "HIGH", f"R:R planejado={planned_rr:.3f}",
                f"retestar bloqueio R:R >= {self.policy.minimum_planned_rr}")

        risk_pct = self._optional_number(trade, "risk_pct", "risk_per_trade_pct")
        if risk_pct is not None and risk_pct > self.policy.maximum_risk_pct:
            add("EXCESSIVE_POSITION_RISK", "HIGH", f"risco={risk_pct:.3f}%",
                "reduzir sizing no cenario comparativo e medir drawdown")

        raw_edge = self._optional_number(trade, "raw_edge", "edge")
        if raw_edge is not None and abs(raw_edge) < self.policy.minimum_edge:
            add("WEAK_EDGE", "MEDIUM", f"edge absoluto={abs(raw_edge):.4f}",
                "comparar limiares de edge somente fora da amostra")

        signal_regime = str(trade.get("signal_regime") or "").upper()
        market_regime = str(trade.get("market_regime") or trade.get("regime") or "").upper()
        if signal_regime and market_regime and signal_regime != market_regime:
            add("REGIME_MISMATCH", "HIGH", f"sinal={signal_regime}; mercado={market_regime}",
                "separar resultado por regime e retestar a estrategia compativel")

        if mae_r is not None and mae_r >= self.policy.severe_mae_r and net < 0:
            add("ADVERSE_ENTRY_TIMING", "MEDIUM", f"MAE={mae_r:.3f}R",
                "testar confirmacao ou entrada posterior sem usar dados futuros")

        if mfe_r is not None and net < 0 and mfe_r >= self.policy.missed_profit_r:
            add("PROFIT_NOT_PROTECTED", "HIGH", f"MFE={mfe_r:.3f}R; final={realized_r:.3f}R",
                "comparar break-even, parciais e trailing com a mesma serie")
        if mfe_r is not None and mfe_r-realized_r >= self.policy.excessive_giveback_r:
            add("EXCESSIVE_GIVEBACK", "MEDIUM", f"devolucao={mfe_r-realized_r:.3f}R",
                "testar protecao progressiva sem otimizar no mesmo periodo")

        exit_reason = str(trade.get("exit_reason") or trade.get("close_reason") or "").upper()
        if "STOP" in exit_reason and mfe_r is not None and mfe_r > 0.5:
            add("STOP_AFTER_FAVORABLE_MOVE", "MEDIUM", f"saida={exit_reason}; MFE={mfe_r:.3f}R",
                "verificar momento de ativacao do break-even e trailing")

        if net < 0 and not causes:
            add("UNEXPLAINED_LOSS", "LOW", "nenhum marcador suficiente nos campos recebidos",
                "exportar MFE, MAE, regime, score, R:R, slippage e motivo de saida")

        confidence = "HIGH" if not missing else "MEDIUM" if len(missing) <= 2 else "LOW"
        return {
            "index": index,
            "trade_id": str(trade.get("trade_id") or trade.get("id") or index),
            "symbol": str(trade.get("symbol") or "UNKNOWN").upper(),
            "strategy_id": str(trade.get("strategy_id") or "UNKNOWN"),
            "regime": market_regime or "UNKNOWN",
            "gross_pnl": round(gross, 8),
            "entry_fee": round(entry_fee, 8),
            "exit_fee": round(exit_fee, 8),
            "total_fees": round(total_fees, 8),
            "net_pnl": round(net, 8),
            "realized_r": round(realized_r, 6),
            "outcome": "WIN" if net > 0 else "LOSS" if net < 0 else "FLAT",
            "diagnostic_confidence": confidence,
            "missing_fields": missing,
            "causes": causes,
        }

    def _summarize(self, trades: list[dict[str, Any]]) -> dict[str, Any]:
        pnls = [float(item["net_pnl"]) for item in trades]
        fees = sum(float(item["total_fees"]) for item in trades)
        gross = sum(float(item["gross_pnl"]) for item in trades)
        cause_counts = Counter(
            cause["code"] for item in trades for cause in item["causes"]
        )
        by_strategy: dict[str, float] = defaultdict(float)
        by_regime: dict[str, float] = defaultdict(float)
        equity = peak = drawdown = 0.0
        for item in trades:
            value = float(item["net_pnl"])
            by_strategy[item["strategy_id"]] += value
            by_regime[item["regime"]] += value
            equity += value
            peak = max(peak, equity)
            drawdown = max(drawdown, peak-equity)
        profit = sum(value for value in pnls if value > 0)
        loss = abs(sum(value for value in pnls if value < 0))
        return {
            "trade_count": len(trades),
            "wins": sum(value > 0 for value in pnls),
            "losses": sum(value < 0 for value in pnls),
            "gross_pnl": round(gross, 8),
            "total_fees": round(fees, 8),
            "net_pnl": round(sum(pnls), 8),
            "profit_factor_net": round(profit/loss, 6) if loss else None,
            "maximum_drawdown_value": round(drawdown, 8),
            "top_diagnostic_causes": [
                {"code": code, "count": count} for code, count in cause_counts.most_common(10)
            ],
            "net_pnl_by_strategy": dict(sorted(by_strategy.items())),
            "net_pnl_by_regime": dict(sorted(by_regime.items())),
            "pnl_basis": "NET_AFTER_FEES",
        }

    @staticmethod
    def _optional_number(data: Mapping[str, Any], *names: str) -> float | None:
        for name in names:
            if name in data and data[name] not in (None, ""):
                value = float(data[name])
                return value if math.isfinite(value) else None
        return None

    @classmethod
    def _number(cls, data: Mapping[str, Any], *names: str, default: float) -> float:
        value = cls._optional_number(data, *names)
        return default if value is None else value
