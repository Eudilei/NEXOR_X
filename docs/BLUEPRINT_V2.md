# NEXOR X — Blueprint V2

## Arquitetura aprovada para a fase atual

O sistema continuará como **monólito modular** até provar necessidade operacional de separação. Dividir precocemente em microserviços aumentaria superfície de falha sem criar edge.

### Domínios

- Core: lifecycle, scheduler, registry, event bus.
- Market: aquisição, cache, qualidade e regime.
- Quant: evidências e avaliação preliminar.
- Laboratory: observações, calibração, edge discovery e validação.
- Portfolio/Risk: estado da carteira e gates.
- Execution/Position: simulação PAPER e gestão pós-entrada.
- API/Command Center: leitura pública e controles autenticados.
- AI: consulta e explicação; nunca autoridade de execução.

## Contrato operacional obrigatório

Market → Evidence → Quant → Probability → Laboratory Robustness → Portfolio → Pre-Trade Gate → Execution.

Nenhum módulo pode pular o Pre-Trade Gate. A IA não pode chamar o executor diretamente.

## Barreiras para LIVE

Antes de criar o primeiro conector de ordem real:

1. ledger imutável de dupla entrada;
2. idempotência e client order id;
3. reconciliação contínua com exchange;
4. testnet e chaos tests;
5. walk-forward purgado com embargo;
6. Monte Carlo por blocos e por regime;
7. custos, funding e slippage observados;
8. certificação CQO reproduzível;
9. autenticação forte e RBAC;
10. rollback e kill switch externo.
