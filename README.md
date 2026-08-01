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
