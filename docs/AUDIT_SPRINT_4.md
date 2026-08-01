# Auditoria — Sprint 4

## Escopo

Primeira implementação do Market Intelligence Engine e endurecimento do adaptador de dados.

## Controles implementados

- classificação determinística e explicável;
- nenhuma saída é tratada como probabilidade de lucro;
- validação estrita de símbolo;
- cache curto para reduzir chamadas externas;
- cooldown após falha para evitar repetição de HTTP 451/rate-limit;
- retorno do último snapshot com marcação explícita de cache/stale;
- estado geral DEGRADED quando um serviço essencial está degradado;
- endpoint de diagnóstico sem segredos;
- favicon 404 removido;
- LIVE permanece bloqueado.

## Limites conhecidos

- O classificador usa apenas o snapshot de 24 horas nesta fase.
- Não existe estratégia, ordem, position sizing ou edge comprovado.
- O ambiente de hospedagem pode bloquear a Binance; sem cache inicial o endpoint retorna 503.
- A confiança é confiança da regra de classificação, não chance de ganho.

## Critério CQO

A Sprint é aprovada como infraestrutura de percepção inicial, não como motor de trading.
A próxima validação deve introduzir séries temporais reais e testes de regime fora da amostra.
