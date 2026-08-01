# NEXOR X

Quantitative Trading Operating System voltado a descoberta, validacao e exploracao controlada de vantagem estatistica.

## Estado atual

**Sprint 3 — Public Web Command Center**

- PAPER por padrao, com dados reais da Binance Futures.
- LIVE bloqueado ate certificacao futura do laboratorio.
- Kernel, Event Bus, Registry, Scheduler, Watchdog e SQLite.
- Command Center responsivo na porta 8809, com WebSocket e endpoint de saude.
- Implantacao publica preparada para Render por `render.yaml`.
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

Abra `http://127.0.0.1:8809`. Para publicar como site HTTPS, consulte `docs/DEPLOY_RENDER.md`.

## Seguranca

Nunca envie `.env`, bancos, logs ou chaves para o GitHub. O projeto permanece incapaz de enviar ordens nesta etapa.


## Sprint 4 — Market Intelligence

- Classificador explicável de regime de mercado.
- Cache de dados, cooldown de falhas e modo degradado.
- Endpoint `/api/market/{symbol}` com snapshot e estado.
- Command Center com regime, direção, confiança e frescor dos dados.
- Nenhuma decisão de trade é tomada nesta Sprint.

## Sprint 5 — Evidence Engine e Quant Brain

A plataforma agora transforma o estado de mercado em evidências independentes e produz uma avaliação explicável de viés (`LONG_BIAS`, `SHORT_BIAS`, `NO_EDGE` ou `INSUFFICIENT_DATA`). Essa avaliação ainda não é calibrada e jamais autoriza execução. Endpoint: `/api/quant/{symbol}`.
