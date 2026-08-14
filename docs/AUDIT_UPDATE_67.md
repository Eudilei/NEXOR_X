# Update 67 — Net PnL Runtime Integration

## Regra operacional

O campo principal `pnl` de um trade fechado deve representar o valor líquido
depois das taxas.

Campos preservados:
- gross_pnl
- entry_fee
- exit_fee
- total_fees
- net_pnl

Aliases operacionais:
- pnl = net_pnl
- realized_pnl = net_pnl
- pnl_basis = NET_AFTER_FEES

## Métricas

Profit Factor e PnL acumulado passam a priorizar `net_pnl`.

Trades antigos continuam compatíveis via fallback.

LIVE permanece bloqueado.
