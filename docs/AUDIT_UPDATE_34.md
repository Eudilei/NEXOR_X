# Update 34 — Backtest Contextual Automático Pré-Entrada

## Objetivo

Executar uma validação histórica rápida imediatamente antes de qualquer entrada
PAPER do bot, usando somente operações já encerradas do mesmo:

- ativo;
- direção;
- regime de mercado.

## Métricas obrigatórias

- quantidade mínima de amostras;
- Profit Factor;
- Expected R;
- desempenho recente;
- drawdown histórico em R;
- taxa de aprovação por janelas temporais.

## Integração

O Backtest Contextual passa a fazer parte de `trading_readiness`.

Mesmo quando o Pre-Trade Gate tradicional aprova o sinal, a entrada PAPER será
bloqueada se o contexto histórico atual não passar.

A validação é deliberadamente leve, usando no máximo as 300 observações mais
recentes do contexto, para não atrasar excessivamente a entrada.

## Segurança metodológica

- não usa o resultado da operação atual;
- não inventa amostras ausentes;
- amostra insuficiente bloqueia a entrada;
- degradação recente bloqueia a entrada;
- LIVE permanece bloqueado.

## Camadas

O sistema passa a usar duas camadas complementares:

1. validações completas periódicas do laboratório;
2. backtest contextual rápido imediatamente antes da entrada.
