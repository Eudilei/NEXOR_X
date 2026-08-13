# Configuração de credenciais externas

O NEXOR X mantém campos separados para Binance e Telegram por variáveis de ambiente.

## Binance

```text
BINANCE_API_KEY=
BINANCE_API_SECRET=
BINANCE_USE_TESTNET=true
```

Enquanto o sistema estiver em Simulação/Rede de testes, `BINANCE_USE_TESTNET`
deve permanecer como `true`.

O sistema nunca deve mostrar o valor das chaves pelo painel ou pela API. Apenas
o estado "configurado / não configurado" pode ser exibido.

## Telegram

```text
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

Esses campos serão usados pelo serviço de notificações do NEXOR X.

## Segurança

- `.env` real não deve ir para o GitHub;
- apenas `.env.example` pode ser versionado;
- chaves LIVE devem ser inseridas somente quando a fase LIVE for formalmente liberada;
- o painel nunca retorna os valores das credenciais;
- esta atualização não libera LIVE.
