# Auditoria — Sprint 11

## Escopo

Edge Discovery Engine baseado exclusivamente em observações encerradas. Os contextos são segregados por direção, regime, faixa de edge e, quando aplicável, símbolo.

## Controles contra falso edge

- amostra mínima por contexto;
- separação cronológica em duas metades, ambas com expectativa positiva;
- Profit Factor mínimo;
- expectativa mínima em R;
- intervalo inferior de Wilson para taxa de acerto;
- teste binomial unilateral;
- correção Benjamini–Hochberg para múltiplas hipóteses;
- persistência de candidatos aprovados e rejeitados;
- nenhuma autorização de execução ou certificação LIVE.

## Limitações deliberadas

O motor descobre relações somente entre os campos atualmente persistidos em `quant_observations`. Ele não inventa causalidade e não afirma que um padrão histórico continuará lucrativo. Todo candidato ainda exige validação fora da amostra, walk-forward e campanha PAPER.
