# Update 39 — Alertas Telegram Operacionais

## Objetivo

Transformar o Telegram configurado na Update 35 em um canal operacional útil,
sem gerar mensagens a cada varredura.

## Eventos enviados

- inicialização do NEXOR X;
- entrada PAPER;
- fechamento PAPER;
- ciclo automático quando abriu posição ou teve erro;
- gestão automática quando executou alguma proteção;
- reconciliação;
- Supervisor Operacional;
- campanha e ciclo de validação.

## Antispam

Ciclos sem entrada, sem erro e sem ação de proteção não geram mensagem.

## Segurança

- nenhuma API key ou token é incluído nas mensagens;
- notificações podem ser desligadas por variável de ambiente;
- falha no Telegram não altera o modo de operação;
- LIVE permanece bloqueado.


## Validação local
O notificador foi mantido desacoplado da classe concreta Event, facilitando teste isolado sem alterar o contrato do EventBus.
