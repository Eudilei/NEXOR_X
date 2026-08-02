# Auditoria — Sprint 12

## Escopo

Probability Calibration Engine temporal, comparando Platt Scaling e regressão isotônica sem dependência externa de machine learning.

## Controles implementados

- separação por direção e regime;
- mínimo de amostras independente da calibração binária anterior;
- treino em período anterior e seleção de método em holdout posterior;
- Brier Score de treino e validação;
- Expected Calibration Error (ECE);
- intervalo de confiança de 95%;
- Expected R e Profit Factor observados;
- Kelly fracionado limitado;
- bloqueio explícito de execução e LIVE.

## Tentativas de reprovação

- amostra insuficiente;
- probabilidades fora de 0–1;
- contexto misturado entre LONG/SHORT e regimes;
- modelo isotônico não monotônico;
- Kelly negativo ou acima de 100%;
- endpoint liberando execução.

## Limitações honestas

- os modelos não provam causalidade;
- o intervalo de confiança é uma aproximação de Wilson aplicada à probabilidade estimada;
- a seleção entre dois calibradores ainda pode sofrer seleção de modelo;
- a saída não deve ser usada para ordens até walk-forward, Monte Carlo e certificação CQO.

## Resultado automatizado

- compilação integral: aprovada;
- testes: 72 aprovados, 0 falhas.
