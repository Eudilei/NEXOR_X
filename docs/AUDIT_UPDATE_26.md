# Update 26 — Operational Supervisor

## Objetivo

Criar um gate operacional central acima dos gates individuais já existentes.

## Regras

- PAPER exige dados frescos, ausência de hard stop, zero falhas críticas e zero incidentes;
- TESTNET exige tudo do PAPER mais reconciliação limpa, exchange pronta e conector testado;
- LIVE permanece sempre falso;
- certificação técnica nunca ativa LIVE automaticamente;
- pedido explícito de modo LIVE é ignorado e registrado como warning.

## Motivo

À medida que o NEXOR X ganhou vários subsistemas, decisões operacionais ficaram
distribuídas. O Supervisor cria uma decisão única e auditável para o estado operacional.
