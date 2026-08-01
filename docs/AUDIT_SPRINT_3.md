# Auditoria — Sprint 3

## Escopo

Publicação do Command Center como serviço web HTTPS, mantendo o NEXOR X em PAPER.

## Verificações executadas

- 11 testes automatizados aprovados.
- Compilação de `src` e `tests` aprovada.
- `PORT` do provedor sobrescreve a porta local corretamente.
- Bind em `0.0.0.0` confirmado.
- Endpoint `/health` adicionado para o provedor.
- `render.yaml` mantém `NEXOR_MODE=PAPER` e `ALLOW_LIVE_MODE=false`.
- Segredos declarados com `sync: false`; nenhum valor secreto incluído.
- Banco temporário isolado em `/tmp` no serviço gratuito.

## Tentativa de reprovação

1. Porta dinâmica do provedor: aprovada.
2. Inicialização sem chaves Binance/Telegram: permanece degradada, mas o painel inicia.
3. Ollama local indisponível no Render: falha isolada no serviço de IA, sem derrubar o site.
4. Binance retornar 451: serviço marcado como falho/degradado, sem derrubar a API.
5. Tentativa de ativar LIVE sem certificação: bloqueada pelo validador.

## Limitações conhecidas

- Plano gratuito pode suspender o serviço por inatividade.
- SQLite em `/tmp` não é persistente.
- Ollama precisa de endpoint externo ou execução local.
- Ainda não há autenticação do painel; nesta fase não são expostos segredos nem funções de ordem.
