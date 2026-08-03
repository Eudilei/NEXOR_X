# NEXOR X — Auditoria Arquitetural Adversarial (Sprint 13)

## Veredito executivo

A arquitetura anterior foi **reprovada para qualquer exposição pública sem autenticação** e **reprovada para certificação LIVE**.

A base é adequada como monólito modular em PAPER, mas ainda não é uma arquitetura de serviços distribuídos. O Kernel chama vários componentes diretamente; o Event Bus é hoje uma trilha de eventos e persistência, não o mecanismo exclusivo de comunicação descrito originalmente.

## Falhas críticas encontradas e corrigidas

1. **API administrativa pública**
   - Endpoints POST permitiam scanner manual, descoberta de edge, abertura/fechamento PAPER, gestão de posições e uso do Ollama sem autenticação.
   - Correção: `X-NEXOR-ADMIN-TOKEN` obrigatório; sem token configurado os controles ficam desabilitados.

2. **Atualizações financeiras não atômicas**
   - A posição e a carteira eram atualizadas em commits separados. Uma interrupção entre commits poderia gerar divergência contábil.
   - Correção: transações SQLite com `BEGIN IMMEDIATE`, commit único e rollback integral.

3. **Taxa de entrada contabilizada tardiamente**
   - A equity PAPER não refletia a taxa paga no momento da abertura.
   - Correção: a taxa de entrada é debitada de equity e PnL realizado na mesma transação da abertura. Fechamentos posteriores contabilizam apenas o delta ainda não reconhecido na conta.

4. **Intervalo de confiança estatisticamente inadequado**
   - Um intervalo de Wilson era aplicado diretamente sobre uma probabilidade ajustada pelo modelo.
   - Correção: intervalo percentil por bootstrap determinístico da predição calibrada.

5. **Métricas de calibração otimistas**
   - Brier Score e ECE reportados eram calculados após ajuste com toda a amostra.
   - Correção: métricas principais passam a usar o holdout temporal.

## Falhas estruturais mantidas como dívida técnica controlada

- SQLite executa chamadas síncronas sob lock dentro do loop assíncrono. Aceitável para PAPER de baixa carga; inadequado para alta frequência.
- Watchdog detecta falha, mas não reinicia serviços. A documentação anterior superestimava sua capacidade.
- O Command Center está embutido em uma string HTML extensa dentro da API.
- Não existe versionamento de schema formal; há apenas migrações incrementais locais.
- Não existe autenticação de usuário, sessão, RBAC ou proteção CSRF. O token administrativo é uma barreira mínima de operação, não um sistema completo de identidade.
- Não há execução LIVE, reconciliação de exchange, idempotência de ordens, relógio de exchange nem ledger de dupla entrada.
- Não há prova de edge econômico. Os testes validam software, não lucratividade.

## Classificação correta da arquitetura

**Hoje:** monólito modular assíncrono, com persistência SQLite, API FastAPI e eventos internos.

**Não é hoje:** microserviços, sistema distribuído, plataforma institucional certificada ou motor LIVE.

## Decisão CQO

- PAPER: permitido para desenvolvimento e coleta.
- Site público: permitido somente com token administrativo configurado.
- LIVE: bloqueado.
- Próximo marco científico: Monte Carlo + walk-forward purgado/embargado.
- Próximo marco de engenharia: ledger contábil, migrations formais, fila durável e autenticação completa.
