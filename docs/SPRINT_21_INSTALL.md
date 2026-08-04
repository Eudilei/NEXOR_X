# Instalação da Sprint 21

```bash
python tools/apply_sprint21.py
python -m compileall -q src tests tools
python -m pytest -q tests/test_binance_live_connector.py tests/test_reconciliation.py
python -m pytest -q
```

Endpoint:

- `GET /api/exchange/live-readiness` — exige `X-NEXOR-ADMIN-TOKEN`

O conector inicia em TESTNET e não possui métodos para enviar ordens.
