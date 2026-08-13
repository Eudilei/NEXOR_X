# Update 45 — Post-Recovery Probation Gate

## Objetivo

A Update 44 impede liberação precoce depois de degradação. A Update 45
controla a etapa imediatamente seguinte: a retomada de novas exposições.

## Política padrão

Depois de `RECOVERED`:

- provação mínima de 60 minutos;
- apenas estado `NORMAL` pode aumentar exposição;
- intervalo mínimo de 15 minutos entre admissões;
- no máximo 3 novas admissões durante a provação;
- `CAUTION` bloqueia novas exposições durante a provação;
- `reduce_only` permanece liberado.

## Persistência

`data/entry_probation_state.json`

## Efeito

A retomada deixa de ser binária. Primeiro o sistema prova estabilidade,
depois retorna ao fluxo normal de entrada.

## Segurança

A Update 45 não cria qualquer caminho de execução LIVE.
`live_allowed=false` permanece invariável.
