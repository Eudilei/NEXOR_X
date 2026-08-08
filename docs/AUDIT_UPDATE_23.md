# Update 23 — Runtime Update Engine

## Objetivo

Eliminar dependência de Codespaces para atualizações normais e criar uma trilha
persistente das versões que realmente inicializaram com sucesso.

## Arquitetura

O GitHub Actions continua sendo o executor de atualização:

1. valida o ZIP;
2. aplica o payload em uma cópia do checkout;
3. executa migração opcional;
4. instala dependências;
5. compila;
6. executa lint crítico;
7. executa todos os testes;
8. somente então faz commit.

O Runtime Update Engine não baixa nem executa código remoto. Ele registra no banco a
versão que chegou a inicializar após o commit.

## Segurança

- nenhuma atualização é aplicada pelo processo de trading;
- nenhuma atualização muda PAPER para LIVE;
- falha de testes impede o commit automático;
- a atualização não depende mais de Codespaces;
- versões aplicadas ficam auditáveis no banco.


## Correção de compatibilidade

Os instaladores legados `tools/apply_sprint*.py` não são removidos nesta atualização.
A suíte de regressão atual ainda contém testes que verificam explicitamente a presença
desses arquivos. A limpeza será feita somente em uma futura migração coordenada que
também substitua esses testes.
