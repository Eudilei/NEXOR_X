# Sprint 20 — CQO Certification Engine

## Implementado

- certificado técnico baseado em evidências quantitativas e operacionais;
- mínimo de operações PAPER;
- PF e Expected R globais e recentes;
- drawdown máximo;
- walk-forward;
- Monte Carlo;
- Brier e ECE fora da amostra;
- incidentes operacionais;
- falhas críticas de teste;
- tempo mínimo em PAPER;
- frescor de dados;
- reconciliação;
- configuração de segredos;
- teste do conector LIVE;
- aprovação manual separada.

## Regra de segurança

Mesmo quando todos os critérios passam, o retorno mantém:

- `live_execution_allowed = false`
- `mode_switch_available = false`

A Sprint 20 certifica evidência, mas não altera o modo do sistema.

## Tentativas de reprovação

- amostra pequena;
- degradação recente;
- drawdown elevado;
- walk-forward fraco;
- risco de ruína;
- calibração ruim;
- incidente operacional;
- falha de reconciliação;
- conector LIVE não testado;
- ausência de aprovação manual.
