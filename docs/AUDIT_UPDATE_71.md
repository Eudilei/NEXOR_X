# Update 71 — Historical Dataset Evidence Bridge

## O que é reaproveitado

A base mensal Binance `*USDT-5m-AAAA-MM.zip` e os resultados registrados pelo
Laboratório 7.3.15.58 podem ser lidos sem novo download.

## O que é auditado

- hash e tamanho de cada ZIP;
- quantidade e intervalo dos candles;
- validade OHLCV;
- ordem temporal e duplicações;
- intervalos ausentes e maior buraco;
- cobertura por símbolo;
- necessidade de agregação 5m → 15m e contexto 4h;
- indisponibilidade de spread, slippage, livro, OI e funding histórico real.

## Diagnóstico positivo e negativo

Além de causas de perdas, o relatório classifica fatores que funcionaram:
custos controlados, slippage aceitável, R:R saudável, risco controlado, edge
registrado forte, alinhamento de regime, entrada favorável e retenção de lucro.

## Limite de fidelidade

O motor 7.3.15.58 não é tratado como motor final do NEXOR X. Seus resultados
recebem `LEGACY_7_3_15_58_NOT_FINAL_NEXOR_X` e servem somente para diagnóstico.
Uma alegação de replay final exato exige uma autoridade de estratégia baseada
em candles compartilhada pelo runtime e pelo Laboratório. Nenhum parâmetro é
alterado automaticamente e LIVE permanece bloqueado.
