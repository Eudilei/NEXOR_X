# Update 32 — Coletor Automático de Evidências

## Objetivo

Reduzir entradas manuais na campanha de validação e coletar automaticamente
as evidências já persistidas pelo NEXOR X.

## Coleta

- quantidade de operações PAPER;
- Profit Factor;
- Expected R;
- desempenho recente;
- drawdown;
- incidentes;
- falhas críticas;
- saúde de integração;
- Recovery Guard;
- Supervisor Operacional.

## Princípio conservador

Quando uma evidência essencial não existe, o coletor não presume sucesso.

Exemplos:
- sem histórico de trades: PF e Expected R ficam em zero;
- sem drawdown persistido: usa valor conservador que impede avanço;
- sem relatório de integração/recovery/supervisor: estado considerado não aprovado.

## Segurança

O coletor não abre ordens, não altera posições e não muda o modo operacional.


## Correção definitiva de compatibilidade do pacote evidence

A Update 32 não substitui mais `src/nexor_x/evidence/__init__.py`.
O arquivo já existente no repositório possui contratos públicos legados,
incluindo `EvidenceDirection` e `EvidenceEngine`.

O instalador agora apenas adiciona `EvidenceCollector` e `EvidenceSnapshot`
ao pacote existente, preservando todos os símbolos anteriores.
