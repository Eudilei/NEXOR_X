# Update 63 — Autonomous Validation Orchestrator

## Marco de fechamento

Esta update encerra a fase planejada de construção do NEXOR X.

O arquivo `tools/validation_orchestrator.py` coordena as ferramentas
criadas nas Updates 57–62 sem alterar o runtime de trading.

## Ciclo

1. RC verify
2. validation campaign tick
3. evidence progress
4. evidence completion watchdog
5. integrity audit quando houver bundle
6. preauthorization dossier somente após evidência verificada

## Concorrência

`data/validation_orchestrator.lock` impede duas instâncias simultâneas.

## Observabilidade

- `reports/validation_orchestrator_heartbeat.json`
- `reports/validation_orchestrator_history.jsonl`

## Freeze

Após esta versão, novas alterações estruturais devem ocorrer somente
mediante bug real, falha de integração ou risco detectado durante a
validação.

LIVE permanece bloqueado.
