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
