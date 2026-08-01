# Auditoria — Sprint 6

## Escopo

- correção da integração incompleta do Quant Brain no Kernel;
- persistência de observações históricas encerradas;
- calibração causal por contexto e faixa de edge;
- métricas: probabilidade observada, expectativa em R, Profit Factor e Brier Score;
- walk-forward temporal;
- endpoint de status do laboratório;
- bloqueio explícito de execução.

## Falhas encontradas e corrigidas

A revisão adversarial encontrou que a Sprint 5 expunha `/api/quant/{symbol}`, mas o Kernel não implementava `quant_assessment` e também não instanciava `EvidenceEngine` e `QuantBrain`. Isso poderia passar despercebido em testes com dublês de Kernel. A Sprint 6 corrige a integração real e adiciona testes de integração do Kernel.

## Limites

- não existem dados históricos incluídos no pacote;
- nenhuma probabilidade é exibida antes de 30 observações completas no mesmo contexto;
- aprovação no walk-forward não libera LIVE;
- `execution_allowed` permanece sempre `false`.
