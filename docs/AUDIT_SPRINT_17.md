# Sprint 17 — Meta Strategy Orchestrator

## Escopo implementado

- registro tipado de estratégias;
- métricas separadas por regime e direção;
- ranking determinístico e explicável;
- critérios mínimos de amostra, PF, Expected R, calibração, walk-forward e Monte Carlo;
- histerese para reduzir troca excessiva de estratégia;
- persistência de definições, métricas e seleções;
- execução e LIVE permanentemente bloqueados nesta etapa.

## Limites deliberados

O orquestrador não cria sinais, não estima probabilidade, não calcula fills e não envia ordens.
Ele compara métricas já produzidas pelos módulos científicos do NEXOR X.

A seleção `SELECTED_FOR_RESEARCH` não é autorização operacional.

## Tentativas de reprovação cobertas

- estratégia sem amostra mínima;
- PF abaixo do mínimo;
- Expected R insuficiente;
- walk-forward reprovado;
- risco de ruína excessivo;
- calibração inadequada;
- contexto incompatível;
- estratégia aposentada;
- troca excessiva entre candidatos próximos;
- métricas não finitas.

## Próxima integração

A próxima Sprint deverá ligar o módulo ao Kernel e à API administrativa, alimentando as
métricas a partir dos resultados persistidos do Laboratório.
