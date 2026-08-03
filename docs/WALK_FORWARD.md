# Walk-Forward Contínuo

A Sprint 15 adiciona validação temporal por janela expansiva. Cada fold usa somente observações encerradas antes da janela de teste.

Critérios principais:
- amostra mínima de treino e teste;
- seleção causal por Expected R positivo;
- PF mínimo por fold;
- proporção mínima de folds aprovados;
- persistência integral dos resultados.

Endpoints:
- `GET /api/walk-forward/status`
- `POST /api/walk-forward/run` (token administrativo)

Aprovação não libera execução nem LIVE.
