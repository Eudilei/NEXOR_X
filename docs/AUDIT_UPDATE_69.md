# Update 69 — Net PnL Runtime Closure Fix

Esta atualização conecta `NetPnLRuntimeAdapter.normalize_closed_trade()` ao
caminho autoritativo de fechamento do `PaperExecutionService`.

O registro fechado preserva `gross_pnl`, `entry_fee`, `exit_fee`, `total_fees`,
`net_pnl` e `pnl_basis`. Os campos operacionais `pnl` e `realized_pnl` usam o
líquido após as duas taxas.

A taxa de entrada continua debitada na abertura. No fechamento, o saldo recebe
somente o lucro bruto menos a taxa de saída, evitando cobrança duplicada. O
resultado contábil do trade, por sua vez, desconta entrada e saída.

A auditoria passa a inspecionar o caminho real em
`src/nexor_x/execution/service.py` e deve retornar 15/15. Nenhuma execução LIVE
foi habilitada.
