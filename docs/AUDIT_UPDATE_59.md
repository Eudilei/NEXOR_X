# Update 59 — Evidence Progress Recorder

## Escopo

Ferramenta externa e read-only para acompanhar a coleta de evidência após
o congelamento da arquitetura.

## Endpoints consultados

- `/api/live/certification`
- `/api/validation/final-snapshot`
- `/api/validation/release-candidate`

Todos são consultados via GET.

## Persistência

- `reports/evidence_progress_history.jsonl`
- `reports/evidence_progress_latest.json`

## Segurança

O recorder não contém POST, endpoints de ordem ou chamadas diretas a
PAPER/TESTNET.

LIVE permanece bloqueado.
