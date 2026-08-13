# Update 38 — Gestão Autônoma das Posições PAPER

Fecha o ciclo autônomo em Simulação. O gestor acompanha continuamente posições abertas e usa a política já existente de stop protetivo, break-even, parcial e trailing. Por padrão roda a cada 5 segundos.

Também corrige um erro encontrado na Update 37: `PortfolioService.snapshot()` entrega a lista real em `positions`, enquanto `open_positions` é apenas uma contagem.

LIVE permanece bloqueado.


## Correção de compatibilidade da detecção de posições

A suíte antiga da Update 37 usa `open_positions` como lista, enquanto o
`PortfolioService.snapshot()` atual usa `open_positions` como contagem e
`positions` como lista.

A correção definitiva aceita os dois formatos:

- se `open_positions` for lista/tupla, usa o formato legado;
- caso contrário, usa `positions`, que é o formato atual do PortfolioService.

Assim não quebramos testes antigos e também evitamos o erro de tentar transformar
uma contagem inteira em lista.
