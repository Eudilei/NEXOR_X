# Sprint 18 — Integração do Meta Strategy Orchestrator

## Entrega

- serviço de orquestração conectado ao banco;
- catálogo inicial de cinco estratégias em estado RESEARCH;
- persistência de métricas e seleções;
- endpoint público de status;
- endpoint administrativo de ranking;
- evento `strategy.selection`;
- bloqueio explícito de execução e LIVE.

## Limite metodológico

A API recebe métricas já calculadas pelo laboratório. Ela não fabrica métricas e não
escolhe automaticamente estratégias a partir de dados incompletos.

`SELECTED_FOR_RESEARCH` não significa aprovação operacional.

## Tentativa de reprovação

- ranking com amostra pequena;
- PF e Expected R negativos;
- walk-forward insuficiente;
- Monte Carlo com risco elevado;
- calibração inadequada;
- persistência e recuperação da última seleção;
- autenticação administrativa herdada da API;
- aplicação idempotente do patch.
