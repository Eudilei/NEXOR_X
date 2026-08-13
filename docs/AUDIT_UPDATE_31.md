# Update 31 — Gestor da Campanha de Validação

## Objetivo

Iniciar a fase de prova prolongada do NEXOR X em Simulação e Rede de testes.

## O gestor acompanha

- dias em validação;
- quantidade de operações em Simulação;
- Profit Factor;
- Expected R;
- drawdown;
- desempenho recente;
- saúde de integração;
- Recovery Guard;
- Supervisor Operacional;
- incidentes;
- falhas críticas.

## Estados

- VALIDATION_IN_PROGRESS
- PAUSED_BY_RISK
- EVIDENCE_MILESTONE_REACHED

## Regra

Atingir o marco de evidência não libera operação real. O sistema exige revisão CQO.
LIVE permanece bloqueado.
