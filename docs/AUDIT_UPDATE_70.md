# Update 70 — Laboratório de Diagnóstico do Backtest

O diagnóstico opera exclusivamente sobre dados registrados. Ele não inventa
fills nem atribui causalidade quando faltam evidências.

## Contrato mínimo por operação

Recomendado: `trade_id`, `symbol`, `strategy_id`, `regime`, `gross_pnl`,
`entry_fee`, `exit_fee`, `total_fees`, `net_pnl`, `realized_r`, `exit_reason`.

Para diagnóstico aprofundado: `signal_regime`, `market_regime`, `planned_rr`,
`risk_pct`, `raw_edge`, `slippage_bps`, `mfe_r` e `mae_r`.

## Segurança metodológica

- métricas financeiras usam `NET_AFTER_FEES`;
- recomendações são hipóteses para novo teste fora da amostra;
- nenhuma configuração é alterada automaticamente;
- nenhuma ordem é enviada;
- LIVE permanece bloqueado.
