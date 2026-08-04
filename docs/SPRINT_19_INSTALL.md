# Instalação da Sprint 19

```bash
python tools/apply_sprint19.py
python -m compileall -q src tests tools
python -m pytest -q tests/test_adaptive_allocation.py
python -m pytest -q
```

A API adiciona:

- `GET /api/allocation/status`
- `POST /api/allocation/plan` — exige `X-NEXOR-ADMIN-TOKEN`
