# Auditoria Sprint 8 — Execução PAPER

## Escopo

- Execução PAPER somente após aprovação do `PreTradeGate`.
- Persistência de posição, stop, taxas e slippage.
- Fechamento manual determinístico com PnL líquido.
- Atualização atômica serializada da carteira PAPER.
- Proibição explícita de qualquer envio de ordem LIVE.

## Controles adversariais

1. readiness bloqueada não cria posição;
2. modo LIVE é rejeitado;
3. preço antigo ou inválido é rejeitado;
4. posição duplicada no mesmo símbolo é rejeitada;
5. taxas e slippage são incluídos no PnL;
6. fechamento duplicado é rejeitado;
7. equity, pico e drawdown têm uma única fonte persistente.

## Limites conhecidos

- Não existe execução automática por scheduler nesta Sprint.
- Não existe proteção intrabar nem Profit Harvest ainda.
- Abertura depende de calibração causal real; sem isso será corretamente bloqueada.
- O endpoint de fechamento exige preço informado e é destinado a teste PAPER.
