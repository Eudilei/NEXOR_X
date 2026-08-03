# Auditoria Sprint 14 — Monte Carlo Engine

## Escopo

Foi implementado um diagnóstico de robustez por **moving-block bootstrap** sobre resultados fechados em unidades R. O método reamostra blocos contíguos para preservar parcialmente sequências de ganhos e perdas, evitando a hipótese excessivamente otimista de independência total entre operações.

## Critérios

O relatório é classificado como `ROBUST` somente quando:

- probabilidade simulada de atingir o drawdown de ruína é menor ou igual a 5%;
- drawdown máximo no percentil 95 permanece abaixo do limite configurado.

`ROBUST` não significa lucratividade garantida, não certifica LIVE e não autoriza execução.

## Proteções

- seed persistida para reprodutibilidade;
- amostra mínima obrigatória;
- filtros opcionais por símbolo, direção e regime;
- endpoint de execução protegido por token administrativo;
- persistência integral de parâmetros e resultados;
- `execution_allowed=false` e `live_certified=false` em todas as respostas.

## Limitações conhecidas

- bootstrap não modela mudanças estruturais futuras;
- resultados dependem da qualidade e representatividade das observações;
- custos já devem estar incorporados em `realized_r`;
- não há ainda cenários explícitos de choque de spread, slippage e indisponibilidade;
- a Sprint seguinte deverá integrar walk-forward contínuo e stress de custos.

## Verificação executada

- compilação integral de `src` e `tests`;
- 83 testes coletados;
- 83 testes aprovados, 0 falhas;
- testes de reprodutibilidade, amostra insuficiente, distribuição vencedora, distribuição perdedora, persistência e autenticação da API;
- `ruff` não estava instalado no ambiente de empacotamento e, portanto, não é declarado como executado.
