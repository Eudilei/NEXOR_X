# Update 43 — Entry Admission Guard

## Mudança principal

A Update 42 detecta degradação. A Update 43 leva essa decisão ao ponto onde
uma nova exposição seria criada.

## PAPER

Antes de `paper_open()` chamar o serviço de execução, o Kernel consulta o
Performance Degradation Guard. Em `BLOCKED`, a nova posição não é criada.

Como o AutoPaper abre posições usando `paper_open`, o mesmo bloqueio vale
para o fluxo automático.

## TESTNET

Antes de `testnet_order_create()` criar uma ordem que possa aumentar
exposição, o mesmo gate é avaliado.

Ordens `reduce_only=true` continuam permitidas mesmo durante degradação
crítica, para não impedir redução/encerramento de exposição.

## Não interfere em posições existentes

Stop, break-even, trailing, parcial, reconciliação, cancelamento,
reduce-only e fechamento continuam disponíveis.

## Segurança

`live_allowed=false` permanece invariável.
