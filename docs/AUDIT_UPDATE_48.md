# Update 48 — Transactional Entry Reservation Integration

## Integração efetiva

A Update 47 criou a reserva. A Update 48 conecta essa reserva diretamente aos
métodos `paper_open` e `testnet_order_create`.

A integração usa um context manager:

- `__enter__`: reserva;
- retorno normal, inclusive `return` antecipado: confirma;
- exceção: libera;
- `reduce_only`: bypass.

## Segurança

Isso serializa a criação de novas exposições sem bloquear saídas e proteções.

LIVE permanece bloqueado.
