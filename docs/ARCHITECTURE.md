# NEXOR X — Sprint 1 Architecture

The kernel manages lifecycle only. Services communicate through the asynchronous event bus.
The API accesses state through explicit service contracts.

## Safety
- PAPER is the default.
- LIVE is rejected unless the gate is enabled and credentials exist.
- No order-routing code exists in Sprint 1.
- Ollama is advisory only.
- Secrets are loaded from `.env`, ignored by Git.

## Startup
Configuration → logging → event bus → database → Binance public data → Telegram → Ollama → scheduler → watchdog → API.


## Portfolio e Pre-Trade Gate

O `PortfolioService` é a fonte única do estado de risco da carteira. O `PreTradeGate` combina mercado, Quant Brain, calibração causal e portfólio. Nenhum futuro executor poderá receber uma proposta sem uma decisão explícita desse gate.

## Scanner Service

O `MarketScannerService` recebe uma função assíncrona de avaliação, evitando dependência direta da Binance ou do Quant Brain. Cada símbolo é isolado por semáforo e falhas parciais não cancelam a varredura inteira. Resultados são persistidos em `scanner_runs` e `scanner_candidates`. O scanner somente classifica e ordena observações; execução continua separada pelo Pre-Trade Gate e pelo Paper Execution Service.

## Sprint 14 — Monte Carlo

O laboratório contém agora um `MonteCarloEngine` que opera exclusivamente sobre observações encerradas. Ele usa moving-block bootstrap, persiste parâmetros e distribuições e nunca autoriza execução. O endpoint de disparo é administrativo; o último relatório pode ser consultado publicamente sem revelar segredos.
