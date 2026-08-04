# Instalação

Após copiar esta Sprint sobre a raiz do repositório, execute:

```bash
python tools/apply_sprint18.py
python -m compileall -q src tests tools
python -m pytest -q tests/test_strategy_orchestrator.py tests/test_strategy_service.py
python -m pytest -q
```

O script de aplicação é idempotente e altera somente os pontos de integração no
Kernel, API, versão e README.
