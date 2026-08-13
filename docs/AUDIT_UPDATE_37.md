# Update 37 — Execução Autônoma em Simulação

## Objetivo

Fechar o primeiro ciclo autônomo real do NEXOR X em PAPER:

1. varrer o mercado;
2. receber candidatos;
3. impedir duplicação de símbolo já aberto;
4. executar o gate de pré-entrada;
5. executar o backtest contextual obrigatório;
6. abrir somente a melhor oportunidade aprovada em PAPER;
7. persistir o resultado do ciclo.

## Regra de seletividade

Por padrão, apenas uma nova posição pode ser aberta por ciclo automático.
Isso evita que uma única varredura lote a carteira com sinais altamente
correlacionados.

## Segurança

- o módulo chama somente `paper_open`;
- não chama criação de ordem TESTNET;
- não chama qualquer endpoint LIVE;
- posição já aberta não é duplicada;
- qualquer reprovação do gate ou backtest impede a entrada;
- LIVE continua bloqueado.

## Observação

O `paper_open` executa novamente `trading_readiness`, portanto existe uma segunda
checagem imediatamente antes da abertura simulada.
