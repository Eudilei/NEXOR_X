# Auditoria — Sprint 9

## Escopo

- scanner multiativo configurável;
- concorrência limitada;
- isolamento de falhas por símbolo;
- ranking explicável;
- persistência de execuções e candidatos;
- agendamento automático;
- endpoints e visualização no Command Center;
- proibição explícita de execução automática.

## Evidências executadas

- compilação integral de `src` e `tests`;
- 58 testes aprovados, 0 falhas;
- teste de ranking determinístico;
- teste de persistência;
- teste de falha parcial;
- teste de configuração inválida;
- teste de penalização de dados desatualizados;
- teste do endpoint de status;
- regressão completa das Sprints 1 a 8.

## Tentativa de reprovação

1. Um símbolo com falha não interrompe os demais.
2. Símbolos inválidos são rejeitados antes da primeira varredura.
3. Concorrência zero é rejeitada.
4. Dados marcados como antigos recebem penalidade de ranking.
5. O resultado contém `execution_triggered=false` em todos os caminhos.
6. Uma execução concorrente não cria duas varreduras simultâneas.

## Limitações conhecidas

- `raw_edge` e `rank_score` não são probabilidade de lucro;
- em ambientes que retornam HTTP 451 para Binance, a varredura registra falhas e permanece operacional, mas não produz candidatos reais sem dados válidos;
- o scanner ainda não descobre automaticamente todo o catálogo USDT-M;
- não há abertura automática de operação nesta Sprint;
- o lint Ruff não foi executado porque o pacote não estava instalado no ambiente; compilação e testes foram executados.

## Veredito

A Sprint 9 está aprovada como scanner observacional PAPER. Não está autorizada para seleção autônoma de trades nem para LIVE.
