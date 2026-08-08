# Sprint 22 — Ordens TESTNET idempotentes

## Implementado

- criação de ordens somente em Binance Futures TESTNET;
- assinatura autenticada via conector da Sprint 21;
- chave de idempotência derivada de estratégia, sinal e intenção;
- reserva persistente antes da chamada externa;
- recuperação de resultado duplicado sem nova chamada;
- `newClientOrderId` determinístico;
- validação de MARKET e LIMIT;
- endpoint administrativo de criação.

## Segurança

- conector não TESTNET é rejeitado;
- não existe liberação de LIVE;
- `live_order_sent = false`;
- nenhum modo do sistema é alterado;
- a Sprint não liga automaticamente scanner, estratégia ou portfólio à criação de ordem.

## Tentativas de reprovação

- repetição da mesma intenção;
- ordem MARKET com preço;
- ordem LIMIT sem preço;
- quantidade inválida;
- falha de reserva;
- falha da exchange;
- conector configurado para produção.
