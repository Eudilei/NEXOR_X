# Update 60 — Evidence Completion Watchdog

## Objetivo

Encerrar a fase de acompanhamento automático da validação sem modificar
a arquitetura de trading.

## Critérios de FINAL_EVIDENCE_READY

- RC_READY
- TECHNICALLY_COMPLETE
- Final Validation Campaign COMPLETE
- candidate_ready
- evidence_certified
- LIVE bloqueado em todas as fontes consultadas

## Bundle

Quando todos os critérios são atendidos, o watchdog gera:

- `reports/final_evidence_bundle.json`
- `reports/final_evidence_bundle.sha256`

O SHA-256 permite detectar alteração posterior no conteúdo auditado.

## Segurança

O watchdog usa somente GET e não contém qualquer endpoint de ordem.

`FINAL_EVIDENCE_READY` não habilita LIVE.
