# Update 35 — Campos de credenciais Binance e Telegram

## Objetivo

Padronizar os campos de credenciais externas do NEXOR X e manter o sistema pronto
para futura promoção a LIVE sem expor segredos.

## Implementado

- `.env.example` com Binance, Telegram, painel e Ollama;
- separação explícita entre TESTNET e LIVE;
- endpoint de status de credenciais;
- nenhuma chave é retornada pela API;
- Kernel integra serviço de status;
- LIVE continua bloqueado.

## Campos principais

```text
BINANCE_API_KEY=
BINANCE_API_SECRET=
BINANCE_USE_TESTNET=true

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

NEXOR_ADMIN_TOKEN=
```

## Segurança

O `.env` real deve permanecer fora do repositório.
