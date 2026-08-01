# Publicação do Command Center no Render

O NEXOR X permanece em PAPER. O serviço web publica o Command Center e não libera ordens LIVE.

## Implantação por Blueprint

1. Entre no Render com sua conta GitHub.
2. Clique em **New > Blueprint**.
3. Conecte o repositório `Eudilei/NEXOR_X`.
4. Use a branch `main` e o arquivo `render.yaml` da raiz.
5. Preencha apenas os segredos que realmente usar. Binance e Telegram podem ficar vazios durante a fundação.
6. Clique em **Deploy Blueprint**.

O Render fornecerá uma URL HTTPS terminada em `onrender.com`. Cada atualização aprovada no GitHub poderá gerar nova implantação automaticamente.

## Limitações desta fase

- Ollama local não roda dentro do serviço web gratuito sem um servidor Ollama acessível por URL.
- O banco SQLite usa `/tmp`, portanto é efêmero no serviço gratuito.
- A consulta pública da Binance pode ser bloqueada pela região de saída do provedor. O painel continua online e exibe o serviço como degradado.
- LIVE continua bloqueado por `ALLOW_LIVE_MODE=false`.
