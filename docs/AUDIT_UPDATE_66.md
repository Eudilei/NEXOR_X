# Update 66 — Net PnL & Binance Fee Accounting

## Regra contábil

`net_pnl = gross_pnl - entry_fee - exit_fee`

## Objetivo

O resultado principal do NEXOR deve representar o que efetivamente sobra
depois das taxas.

## Auditoria

O sistema preserva:
- gross_pnl
- entry_fee
- exit_fee
- total_fees
- net_pnl

## PAPER

O calculador suporta taxa estimada por maker/taker.

## Exchange

Caso a corretora informe a taxa efetivamente cobrada, o valor real pode ser
fornecido ao calculador e substitui a estimativa.

## Segurança

Esta update é contábil/observacional.
Não habilita LIVE e não modifica a lógica de trading.
