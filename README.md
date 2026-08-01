# NEXOR X

Quantitative Trading Operating System.

## Sprint 1
Foundation with one-command startup, event bus, registry, watchdog, scheduler, SQLite, API, Command Center, Binance public market data, Telegram and Ollama.

**PAPER is the default. LIVE is blocked by a safety gate. No order execution exists in this sprint.**

## Windows
Double-click `START_NEXOR_X.bat`, then open `http://127.0.0.1:8809`.

## Linux / Codespaces
```bash
chmod +x START_NEXOR_X.sh
./START_NEXOR_X.sh
```

## Tests
```bash
python -m pip install -e ".[dev]"
pytest
```

Copy `.env.example` to `.env` and fill credentials only on your machine. Never commit `.env`.
