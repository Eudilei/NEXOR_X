# Auditoria Update 72

O runtime possuía dependência circular de bootstrap: o gate exigia observações
calibradas antes de abrir PAPER, enquanto não existia produtor automático dessas
observações. A atualização adiciona um produtor shadow causal e isolado.

As observações usam apenas informações disponíveis no ciclo. Posições shadow não
alteram a carteira, não chamam execução PAPER e não enviam ordens TESTNET/LIVE.
Após o encerramento, o resultado líquido em R é persistido na mesma tabela lida
pelos motores atuais de calibração e backtest contextual.
