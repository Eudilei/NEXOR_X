# Auditoria da Sprint 5

## Escopo

Evidence Engine e primeira versão do Quant Brain.

## Controles deliberados

- O Quant Brain não envia ordens.
- `execution_allowed` permanece `false` em todos os resultados.
- A confiança exibida mede concordância e cobertura das evidências; não é probabilidade de lucro.
- O resultado é explicitamente `calibrated: false`.
- Cada evidência registra fonte, racional, força e confiabilidade.
- Dados marcados como antigos reduzem a confiabilidade.

## Tentativas de reprovação

- Entrada sem evidências resulta em `INSUFFICIENT_DATA`.
- Evidências conflitantes resultam em `NO_EDGE`.
- Evidências direcionais consistentes geram apenas viés, nunca autorização de execução.
- Regressão da API e do Market Intelligence permanece coberta pela suíte anterior.

## Limitação conhecida

Ainda não existe calibração histórica, expectativa monetária, custos, slippage, walk-forward ou certificação estatística. Portanto, esta Sprint não comprova edge e não deve operar.
