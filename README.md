# NEXOR X

Quantitative Trading Operating System voltado a descoberta, validacao e exploracao controlada de vantagem estatistica.

## Estado atual

**Sprint 2 — Foundation & Command Center**

- PAPER por padrao, com dados reais da Binance Futures.
- LIVE bloqueado ate certificacao futura do laboratorio.
- Kernel, Event Bus, Registry, Scheduler, Watchdog e SQLite.
- Command Center na porta 8809 com atualizacao por WebSocket.
- Integracao inicial com Binance, Telegram e Ollama.
- Configuracao central em `config/settings.yaml` e segredos opcionais em `.env`.

## Inicio rapido

Windows:

```bat
START_NEXOR_X.bat
```

Linux / Codespaces:

```bash
chmod +x START_NEXOR_X.sh
./START_NEXOR_X.sh
```

Abra `http://127.0.0.1:8809`.

## Seguranca

Nunca envie `.env`, bancos, logs ou chaves para o GitHub. O projeto permanece incapaz de enviar ordens nesta etapa.
