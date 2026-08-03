# Monte Carlo no NEXOR X

Execute pelo endpoint administrativo `POST /api/monte-carlo/run` e consulte o último resultado em `GET /api/monte-carlo/status`.

Exemplo de corpo:

```json
{
  "symbol": "BTCUSDT",
  "decision": "LONG_BIAS",
  "regime": "TREND_UP",
  "simulations": 5000,
  "horizon_trades": 250,
  "block_size": 10,
  "seed": 20260803
}
```

O motor usa apenas observações encerradas e retorna distribuições de equity final, drawdown e probabilidade de ruína. Nenhum resultado libera ordens.
