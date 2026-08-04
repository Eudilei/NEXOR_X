# Sprint 19 — Adaptive Portfolio Allocation

## Implementado

- alocação observacional entre estratégias e símbolos;
- orçamento de risco limitado pelo drawdown da carteira;
- redução de risco em recuperação;
- hard stop de alocação;
- limite por candidato;
- limite por grupo de correlação;
- persistência dos planos;
- endpoints de status e geração administrativa.

## Limites

O plano não movimenta saldo, não abre posições e não altera o Pre-Trade Gate.
`execution_allowed` e `live_certified` permanecem falsos.

## Tentativas de reprovação

- candidato com PF baixo;
- Expected R negativo;
- walk-forward insuficiente;
- risco de ruína elevado;
- drawdown individual excessivo;
- concentração em ativos correlacionados;
- carteira em recuperação;
- hard stop global.
