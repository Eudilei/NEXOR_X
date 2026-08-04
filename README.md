# NEXOR X 0.7.0

Plataforma quantitativa em desenvolvimento, com execução real bloqueada.

## Sprint 6

- Market Intelligence;
- Evidence Engine;
- Quant Brain integrado ao Kernel;
- laboratório causal;
- calibração por contexto e faixa de edge;
- Expected R, Profit Factor e Brier Score;
- walk-forward temporal;
- Command Center web;
- PAPER obrigatório.

## Inicialização

Windows: `START_NEXOR_X.bat`

Linux/Codespaces: `./START_NEXOR_X.sh`

## Endpoints

- `/health`
- `/api/status`
- `/api/market/BTCUSDT`
- `/api/quant/BTCUSDT`
- `/api/laboratory/status`

O sistema ainda não possui certificado de aptidão para LIVE.


## Sprint 7 — Portfolio e Pre-Trade Gate

- estado central de equity, pico, drawdown e exposição;
- critérios causais obrigatórios antes de qualquer futura ordem;
- endpoint `/api/portfolio/status`;
- endpoint `/api/trading/readiness/{symbol}`;
- LIVE continua bloqueado;
- esta Sprint não cria ordens.

## Sprint 8 — PAPER Execution

A plataforma agora persiste posições PAPER apenas após aprovação do Pre-Trade Gate. Taxas,
slippage, stop inicial e PnL líquido são auditáveis. Nenhum endpoint envia ordens à Binance;
LIVE permanece bloqueado.

## Sprint 9 — Scanner multiativo observacional

O NEXOR X agora executa varreduras configuráveis sobre múltiplos contratos USDT-M. A varredura reutiliza Market Intelligence, Evidence Engine, Quant Brain e calibração causal, isola falhas por símbolo, persiste cada execução e publica uma lista ordenada de candidatos no Command Center.

Nesta fase o scanner é estritamente observacional: ele não abre posições automaticamente e não transforma `raw_edge` em probabilidade de lucro. Os endpoints são:

- `GET /api/scanner/status`
- `POST /api/scanner/run`

A configuração fica em `config/settings.yaml`, na seção `scanner`.


## Sprint 11 — Edge Discovery

O laboratório identifica hipóteses de edge por contexto com estabilidade temporal e controle de falsos positivos (Benjamini–Hochberg). Use `POST /api/edges/discover` para executar e `GET /api/edges/status` para consultar o último estudo. Nenhum resultado autoriza execução ou LIVE.

## Sprint 12 — Probability Calibration

Novo endpoint observacional:

```text
GET /api/probability/{symbol}
```

Compara Platt Scaling e calibração isotônica em holdout temporal e retorna probabilidade calibrada, IC95%, Brier Score, ECE, Expected R, Profit Factor e Kelly fracionado. A execução e o modo LIVE continuam bloqueados.


## Sprint 14

- Monte Carlo Engine por moving-block bootstrap
- distribuicao de equity e drawdown
- probabilidade de ruina
- persistencia e endpoints administrativos
- nenhuma autorizacao LIVE

## Sprint 15 — Walk-Forward Contínuo

Validação temporal persistente por janelas expansivas, com filtros contextuais e endpoints `/api/walk-forward/status` e `/api/walk-forward/run`. Aprovação não autoriza execução nem LIVE.


## Sprint 16
Counterfactual Engine para comparar filtros historicos sem alegar causalidade.


## Sprint 18 — Strategy Orchestrator integrado

- registro persistente de estrategias;
- ranking administrativo por contexto;
- endpoints `/api/strategies/status` e `/api/strategies/rank`;
- selecao permanece observacional e nao libera PAPER automatico ou LIVE.
