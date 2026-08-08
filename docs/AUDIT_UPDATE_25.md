# Update 25 — Recovery Guard e Reconciliação Pós-Reinício

## Implementado

- reconciliação de posições abertas locais x Binance Futures TESTNET;
- reconciliação de ordens locais pendentes x ordens abertas na exchange;
- detecção de posição órfã;
- detecção de ordem órfã;
- detecção de divergência de quantidade;
- histórico persistente de relatórios de recuperação;
- guard que bloqueia novas ordens TESTNET quando não existe reconciliação válida;
- endpoint administrativo de reconciliação e status.

## Segurança

O serviço não corrige divergências automaticamente.
Enquanto houver qualquer inconsistência, novas ordens TESTNET ficam bloqueadas.

LIVE permanece indisponível.
