from __future__ import annotations

from datetime import UTC, datetime
from typing import Any



class TelegramEventNotifier:
    """Transforms selected NEXOR events into concise Telegram alerts.

    No secret values are included in messages. Only meaningful operational
    events are subscribed, avoiding scanner/heartbeat spam.
    """

    TOPICS = (
        "system.started",
        "execution.paper_open",
        "execution.paper_close",
        "execution.auto_paper_cycle",
        "position.auto_management_cycle",
        "recovery.reconciled",
        "supervisor.evaluated",
        "validation.campaign_evaluated",
        "validation.cycle_completed",
        "live.readiness_evaluated",
        "live.certification_evaluated",
        "operations.performance_degradation_evaluated",
        "execution.entry_blocked_degradation",
        "execution.entry_recovery_state_changed",
    )

    def __init__(
        self,
        telegram: Any,
        *,
        enabled: bool = True,
    ) -> None:
        self.telegram = telegram
        self.enabled = bool(enabled)

    def subscribe(self, event_bus: Any) -> None:
        if not self.enabled:
            return
        for topic in self.TOPICS:
            event_bus.subscribe(topic, self.handle)

    async def handle(self, event: Any) -> None:
        if not self.enabled:
            return
        message = self._format(event)
        if not message:
            return
        await self.telegram.send(message)

    def _format(self, event: Any) -> str | None:
        payload = dict(event.payload or {})
        topic = event.topic

        if topic == "system.started":
            mode = str(payload.get("mode") or "DESCONHECIDO")
            return (
                "🟢 NEXOR X iniciado\n"
                f"Modo: {self._pt_mode(mode)}\n"
                "Operação real: BLOQUEADA"
            )

        if topic == "execution.paper_open":
            symbol = str(payload.get("symbol") or "-")
            side = self._side(payload.get("side"))
            price = self._number(
                payload.get("price")
                or payload.get("entry_price")
                or payload.get("fill_price")
            )
            quantity = self._number(payload.get("quantity"))
            stop = self._number(
                payload.get("stop_price")
                or payload.get("stop")
            )
            return (
                "🟢 ENTRADA EM SIMULAÇÃO\n"
                f"Ativo: {symbol}\n"
                f"Direção: {side}\n"
                f"Entrada: {price}\n"
                f"Quantidade: {quantity}\n"
                f"Stop: {stop}"
            )

        if topic == "execution.paper_close":
            symbol = str(payload.get("symbol") or "-")
            reason = self._reason(payload.get("reason"))
            pnl = self._number(
                payload.get("pnl")
                or payload.get("realized_pnl")
                or payload.get("net_pnl")
            )
            realized_r = self._number(
                payload.get("realized_r")
                or payload.get("pnl_r")
            )
            return (
                "🔴 POSIÇÃO ENCERRADA — SIMULAÇÃO\n"
                f"Ativo: {symbol}\n"
                f"Motivo: {reason}\n"
                f"Resultado: {pnl}\n"
                f"Resultado em R: {realized_r}"
            )

        if topic == "execution.auto_paper_cycle":
            opened = int(payload.get("opened_positions") or 0)
            errors = int(payload.get("errors") or 0)
            if opened <= 0 and errors <= 0:
                return None
            icon = "🟢" if opened > 0 and errors == 0 else "⚠️"
            return (
                f"{icon} CICLO AUTOMÁTICO DE ENTRADA\n"
                f"Novas posições: {opened}\n"
                f"Erros: {errors}"
            )

        if topic == "position.auto_management_cycle":
            actions = int(payload.get("action_count") or 0)
            closed = int(payload.get("closed_positions") or 0)
            evaluated = int(payload.get("evaluated_positions") or 0)
            if actions <= 0 and closed <= 0:
                return None
            return (
                "🛡️ GESTÃO AUTOMÁTICA DE POSIÇÕES\n"
                f"Posições avaliadas: {evaluated}\n"
                f"Ações de proteção: {actions}\n"
                f"Posições encerradas: {closed}"
            )

        if topic == "recovery.reconciled":
            ok = bool(payload.get("recovery_ok", False))
            issues = int(payload.get("issue_count") or 0)
            return (
                ("✅" if ok else "🚨")
                + " RECONCILIAÇÃO\n"
                + f"Estado: {'OK' if ok else 'BLOQUEADA'}\n"
                + f"Divergências: {issues}"
            )

        if topic == "supervisor.evaluated":
            status = self._status(payload.get("status"))
            paper = self._yes_no(payload.get("paper_allowed"))
            testnet = self._yes_no(payload.get("testnet_allowed"))
            return (
                "🧭 SUPERVISOR OPERACIONAL\n"
                f"Estado: {status}\n"
                f"Simulação permitida: {paper}\n"
                f"Rede de testes permitida: {testnet}\n"
                "Operação real: NÃO"
            )

        if topic == "validation.campaign_evaluated":
            phase = self._status(payload.get("phase"))
            continuing = self._yes_no(payload.get("continue_campaign"))
            return (
                "📊 CAMPANHA DE VALIDAÇÃO\n"
                f"Fase: {phase}\n"
                f"Continuar campanha: {continuing}"
            )

        if topic == "validation.cycle_completed":
            phase = self._status(payload.get("phase"))
            days = int(payload.get("days_running") or 0)
            return (
                "📈 CICLO DE VALIDAÇÃO\n"
                f"Dias acumulados: {days}\n"
                f"Fase: {phase}"
            )

        if topic == "execution.entry_recovery_state_changed":
            transition = str(payload.get("transition", "-"))
            if transition == "LATCHED":
                return (
                    "🔒 BLOQUEIO DE RECUPERAÇÃO ATIVADO\n"
                    "Novas entradas permanecem bloqueadas até ""recuperação confirmada.\n"
                    "LIVE: BLOQUEADO"
                )
            if transition == "RECOVERED":
                return (
                    "✅ RECUPERAÇÃO CONFIRMADA\n"
                    "Cooldown e confirmações saudáveis concluídos.\n"
                    "Novas entradas voltam a seguir os demais gates.\n"
                    "LIVE: BLOQUEADO"
                )
            return None

        if topic == "execution.entry_blocked_degradation":
            reasons = list(payload.get("hard_reasons") or [])
            reason_text = ", ".join(str(item) for item in reasons[:6])
            return (
                "⛔ NOVA ENTRADA BLOQUEADA\n"
                f"Ação: {payload.get('action', '-')}\n"
                f"Estado: {payload.get('state', 'BLOCKED')}\n"
                f"Motivos: {reason_text or '-'}\n"
                "Posições abertas continuam protegidas"
            )

        if topic == "operations.performance_degradation_evaluated":
            state = str(payload.get("state", "NORMAL"))
            hard = list(payload.get("hard_reasons") or [])
            caution = list(payload.get("caution_reasons") or [])
            reasons = hard or caution
            reason_text = ", ".join(str(item) for item in reasons[:6])
            return (
                "🛡️ MONITOR DE DEGRADAÇÃO\n"
                f"Estado: {state}\n"
                f"Novas entradas: {'SIM' if payload.get('new_entries_allowed') else 'BLOQUEADAS'}\n"
                f"Motivos: {reason_text or '-'}"
            )

        if topic == "live.certification_evaluated":
            certified = bool(payload.get("evidence_certified", False))
            blockers = list(payload.get("blockers") or [])
            blocker_text = ", ".join(str(item) for item in blockers[:6])
            return (
                "📊 CERTIFICAÇÃO DE EVIDÊNCIAS\n"
                f"Resultado: {'APROVADA' if certified else 'PENDENTE'}\n"
                f"Bloqueios: {blocker_text or '-'}\n"
                "Operação real: BLOQUEADA"
            )

        if topic == "live.readiness_evaluated":
            ready = bool(payload.get("candidate_ready", False))
            blockers = list(payload.get("blockers") or [])
            blocker_text = ", ".join(str(item) for item in blockers[:6])
            return (
                "🧪 PRONTIDÃO PARA FUTURO LIVE\n"
                f"Infra/validação: {'PRONTA' if ready else 'EM ANDAMENTO'}\n"
                f"Bloqueios: {blocker_text or '-'}\n"
                "Operação real: BLOQUEADA"
            )

        return None

    @staticmethod
    def _number(value: Any) -> str:
        if value is None or value == "":
            return "-"
        try:
            return f"{float(value):.8f}".rstrip("0").rstrip(".")
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _yes_no(value: Any) -> str:
        return "SIM" if bool(value) else "NÃO"

    @staticmethod
    def _pt_mode(value: str) -> str:
        mapping = {
            "PAPER": "SIMULAÇÃO",
            "TESTNET": "REDE DE TESTES",
            "LIVE": "OPERAÇÃO REAL",
        }
        return mapping.get(value.upper(), value)

    @staticmethod
    def _side(value: Any) -> str:
        mapping = {
            "LONG": "COMPRA",
            "BUY": "COMPRA",
            "SHORT": "VENDA",
            "SELL": "VENDA",
        }
        raw = str(value or "-").upper()
        return mapping.get(raw, raw)

    @staticmethod
    def _reason(value: Any) -> str:
        mapping = {
            "PROTECTIVE_STOP": "STOP DE PROTEÇÃO",
            "PROFIT_PARTIAL": "REALIZAÇÃO PARCIAL",
            "MANUAL": "MANUAL",
            "TAKE_PROFIT": "ALVO DE LUCRO",
            "TRAILING_STOP": "STOP MÓVEL",
        }
        raw = str(value or "-").upper()
        return mapping.get(raw, raw.replace("_", " "))

    @staticmethod
    def _status(value: Any) -> str:
        mapping = {
            "PAPER_AND_TESTNET_READY": (
                "SIMULAÇÃO E REDE DE TESTES PRONTAS"
            ),
            "PAPER_ONLY": "SOMENTE SIMULAÇÃO",
            "LOCKED": "BLOQUEADO",
            "VALIDATION_IN_PROGRESS": "VALIDAÇÃO EM ANDAMENTO",
            "PAUSED_BY_RISK": "PAUSADA POR RISCO",
            "EVIDENCE_MILESTONE_REACHED": (
                "MARCO DE EVIDÊNCIA ATINGIDO"
            ),
            "READY_FOR_LONG_RUN_VALIDATION": (
                "PRONTO PARA VALIDAÇÃO PROLONGADA"
            ),
        }
        raw = str(value or "-").upper()
        return mapping.get(raw, raw.replace("_", " "))
