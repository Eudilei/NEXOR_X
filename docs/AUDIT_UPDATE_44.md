# Update 44 — Recovery Hysteresis Guard

## Problema resolvido

Evita alternância rápida entre `BLOCKED` e `NORMAL`, reduzindo o risco de
reabrir exposição cedo demais depois de uma degradação crítica.

## Recuperação padrão

Após `BLOCKED`:
- cooldown mínimo de 15 minutos;
- 3 leituras `NORMAL`;
- intervalo mínimo de 5 minutos entre leituras;
- `CAUTION` zera a sequência de recuperação;
- novo `BLOCKED` também zera a recuperação.

## Persistência

Estado em `data/entry_recovery_state.json`, salvo de forma atômica.

## Fluxo

Performance Degradation -> Recovery Hysteresis -> Entry Admission -> PAPER/TESTNET

## Segurança

Posições existentes e reduce-only continuam protegidos pela arquitetura
anterior. `live_allowed=false` permanece invariável.
