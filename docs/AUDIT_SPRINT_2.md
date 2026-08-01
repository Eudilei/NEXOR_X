# Auditoria — Sprint 2

## Escopo entregue

- Configuracao central em YAML, com sobreposicao segura por variaveis de ambiente.
- Segredos mascarados na API publica.
- Command Center com atualizacao WebSocket.
- Endpoint de configuracao somente leitura.
- Validacao de simbolos de mercado.
- Contexto factual para a IA local.
- Limpeza de artefatos indevidos: bancos, caches e bytecode nao fazem parte do pacote.

## Limites intencionais

- Nenhuma ordem e enviada nesta Sprint.
- O modo LIVE continua bloqueado por configuracao e validacao.
- O painel mostra infraestrutura; estrategias e laboratorio ainda serao implementados.

## Tentativas de reprovacao

- Configuracao LIVE sem certificacao: bloqueada.
- Configuracao LIVE sem credenciais: bloqueada.
- Exposicao de segredos por `/api/config`: mascarada.
- Simbolo malformado na API de mercado: rejeitado.
- Queda do WebSocket: cliente tenta reconectar.
