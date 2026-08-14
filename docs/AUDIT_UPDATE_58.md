# Update 58 — Validation Campaign Runner

## Escopo

Ferramenta operacional externa. Não altera módulos de execução, estratégia,
sizing, risk management, PAPER ou TESTNET.

## Fluxo

A cada ciclo:

1. POST `/api/validation/final-campaign/tick`
2. GET `/api/validation/final-snapshot`
3. GET `/api/validation/release-candidate`
4. grava histórico JSONL
5. atualiza snapshot JSON atual

## Intervalo

O runner não aceita intervalo inferior a 1800 segundos, alinhado à política
da Final Validation Campaign.

## Segurança

Não existe chamada a endpoint de ordem.

LIVE permanece bloqueado.
