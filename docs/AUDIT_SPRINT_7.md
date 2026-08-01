# Auditoria Sprint 7 — Portfolio e Pre-Trade Gate

## Escopo

A Sprint 7 cria uma fonte única para equity, pico, drawdown, posições abertas e exposição. Também cria a primeira barreira formal antes de qualquer futura execução.

## Regras implementadas

Uma oportunidade só pode receber `READY_FOR_PAPER` quando, simultaneamente:

- o modo é PAPER;
- existe viés LONG ou SHORT;
- o contexto está calibrado causalmente;
- a amostra mínima foi atingida;
- Expected R é positivo e supera o mínimo configurado;
- Profit Factor contextual supera o mínimo configurado;
- os dados de mercado estão atuais;
- há capacidade de portfólio;
- o hard stop de drawdown não foi atingido.

Mesmo em `READY_FOR_PAPER`, esta Sprint não cria ordens. O campo `order_created` permanece sempre falso e LIVE permanece proibido.

## Tentativas de reprovação

- contexto não calibrado;
- dados antigos;
- ausência de direção;
- PF insuficiente;
- Expected R insuficiente;
- capacidade esgotada;
- hard stop atingido;
- tentativa em LIVE;
- inicialização repetida da conta PAPER.

## Resultado

A arquitetura agora impede que futuros módulos de execução contornem critérios de laboratório, portfólio ou risco. A execução PAPER será adicionada apenas após usar este gate como dependência obrigatória.
