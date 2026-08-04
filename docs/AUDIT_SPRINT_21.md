# Sprint 21 — Binance LIVE Readiness e Reconciliação

## Implementado

- conector autenticado Binance Futures;
- assinatura HMAC SHA-256;
- sincronização de horário;
- recvWindow configurável;
- TESTNET como padrão;
- leitura autenticada da conta;
- diagnóstico de prontidão;
- comparação entre posições locais e posições da exchange;
- detecção de posição órfã e divergência de quantidade.

## Segurança

Não existe método de criação, alteração ou cancelamento de ordem nesta Sprint.
O relatório sempre retorna `live_order_permission = false`.

## Tentativas de reprovação

- credenciais ausentes;
- ping indisponível;
- falha de sincronização temporal;
- acesso assinado rejeitado;
- posição somente na exchange;
- posição somente no ledger local;
- divergência de quantidade;
- tolerância numérica.
