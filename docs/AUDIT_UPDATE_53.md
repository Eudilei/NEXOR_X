# Update 53 — Final Validation Campaign

## Finalidade

Acumular evidência de que a arquitetura continua coerente ao longo do tempo,
em vez de aceitar um único `PASS` instantâneo.

## Política padrão

- 20 amostras PASS válidas
- pelo menos 30 minutos entre amostras
- pelo menos 24 horas de duração total
- FAIL zera somente a sequência consecutiva
- polling rápido não conta

## Persistência

`data/final_validation_campaign.json`

## Relação com a certificação

Esta campanha não substitui a Update 41. Mesmo quando estiver `COMPLETE`,
a certificação de evidências (dias, trades, PF, drawdown etc.) continua sendo
obrigatória antes de qualquer discussão sobre LIVE.

LIVE permanece bloqueado.
