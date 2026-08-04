# Instalação da Sprint 17

Esta entrega é incremental e deve ser copiada sobre a raiz atual do NEXOR X.

Depois da instalação:

```bash
python -m compileall -q src tests
pytest -q tests/test_strategy_orchestrator.py
pytest -q
```

O módulo ainda não é chamado pelo Kernel. Isso é deliberado: primeiro o núcleo de
orquestração é validado isoladamente; a conexão com API, Kernel e Command Center será
feita na Sprint seguinte sem alterar a execução PAPER atual.
