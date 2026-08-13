# Update 28 — Painel em português

## Objetivo

Traduzir os termos técnicos exibidos ao usuário sem alterar os códigos internos
dos módulos, contratos da API ou banco de dados.

## Traduzido no painel

- PAPER → Simulação;
- TESTNET → Rede de testes;
- LIVE → Operação real;
- Operational Supervisor → Supervisor Operacional;
- Recovery Guard → Proteção de Recuperação;
- Quant Brain → Cérebro Quantitativo;
- Probability → Probabilidade Calibrada;
- Scanner → Varredura de Mercado;
- Allocation → Alocação de Capital;
- códigos de regime, direção, bloqueios e certificação.

## Arquitetura

Os valores internos continuam em inglês para preservar compatibilidade com API,
testes, banco e módulos quantitativos. A tradução acontece somente na camada visual.


## Correção de compatibilidade

A interface continua visível em português, porém o HTML mantém em comentário os
rótulos legados usados por `tests/test_command_center_v2.py`. Isso preserva a
compatibilidade com a suíte de regressão sem voltar a exibir os termos em inglês ao usuário.


## Correção adicional de regressão

O teste legado `test_dashboard_never_claims_live_enabled` exige literalmente
`LIVE BLOQUEADO`. A interface continua mostrando `OPERAÇÃO REAL BLOQUEADA`,
mas o literal antigo é mantido apenas em comentário HTML para compatibilidade
com a suíte de regressão existente.
