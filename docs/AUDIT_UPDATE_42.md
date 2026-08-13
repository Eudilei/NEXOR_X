# Update 42 — Performance Degradation Guard

## Objetivo

Não basta uma estratégia ter sido boa no passado. A Update 42 acrescenta uma
camada de vigilância sobre a amostra recente para detectar perda de qualidade.

## Estados

- **NORMAL**: novas entradas seguem liberadas no modo atual.
- **CAUTION**: há deterioração moderada; mantém entradas, mas gera alerta.
- **BLOCKED**: deterioração crítica; novas entradas devem ser suspensas.

## Limites padrão

| Indicador | Cautela | Bloqueio |
|---|---:|---:|
| Profit Factor | < 1.20 | < 1.00 |
| Drawdown | >= 10% | >= 15% |
| Perdas consecutivas | >= 4 | >= 6 |

PF e drawdown só são julgados com pelo menos 20 trades recentes. A sequência
de perdas é uma proteção de emergência e pode bloquear antes disso.

## Posições abertas

`manage_existing_positions=true` mesmo no estado BLOCKED. O objetivo é impedir
novas exposições sem desligar stops, proteção de lucro, trailing ou reconciliação.

## Segurança

`live_allowed=false` permanece invariável nesta atualização.
