# Update 33 — Ciclo Automático de Validação

## Objetivo

Eliminar a necessidade de copiar manualmente as evidências coletadas para o
Gestor da Campanha de Validação.

## Fluxo

1. coleta as evidências persistidas pelo NEXOR X;
2. calcula automaticamente há quantos dias a campanha está ativa;
3. envia as evidências ao Gestor da Campanha;
4. persiste o resultado consolidado;
5. disponibiliza status por API;
6. executa o ciclo periodicamente pelo Scheduler.

## Segurança

- não cria ordens;
- não altera posições;
- não muda PAPER/TESTNET/LIVE;
- LIVE permanece sempre falso;
- dados ausentes continuam sendo tratados de forma conservadora pelo coletor.
