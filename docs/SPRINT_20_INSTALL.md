# Instalação da Sprint 20

```bash
python tools/apply_sprint20.py
python -m compileall -q src tests tools
python -m pytest -q tests/test_cqo_certification.py
python -m pytest -q
```

Endpoints:

- `GET /api/certification/status`
- `POST /api/certification/evaluate` — exige `X-NEXOR-ADMIN-TOKEN`
