# Update 41 — Certificação de Evidências

## Objetivo

A Update 40 responde: **a infraestrutura está pronta para ser avaliada?**

A Update 41 responde: **há evidência operacional suficiente para considerar
a validação tecnicamente madura?**

Nenhuma das duas autoriza LIVE.

## Política padrão

| Gate | Limite |
|---|---:|
| Readiness | aprovado |
| Dias de validação | >= 30 |
| Trades fechados | >= 100 |
| Profit Factor | >= 1.20 |
| Drawdown máximo | <= 15% |
| Runtime LIVE | desabilitado |

## Saída

O endpoint `GET /api/live/certification` retorna:

- `evidence_certified`;
- `live_allowed=false`;
- `live_certified=false`;
- métricas observadas;
- política aplicada;
- checks individuais;
- bloqueadores.

## Segurança

Mesmo que todos os gates sejam aprovados, a Update 41 não contém código
para ativar execução com dinheiro real.
