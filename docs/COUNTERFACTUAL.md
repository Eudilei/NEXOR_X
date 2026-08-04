# Counterfactual Engine

A Sprint 16 compara politicas deterministicas de admissao usando somente resultados
historicos ja observados. Ela mede quantos trades seriam mantidos ou bloqueados, perdas
evitadas, lucros perdidos e beneficio liquido historico.

## Limite metodologico

O estudo nao reconstroi fills, nao inventa resultados de trades nao observados e nao prova
causalidade. Um resultado `IMPROVEMENT_FOUND` significa apenas que a politica teria
selecionado um subconjunto historico com resultado melhor dentro da mesma amostra.

## Endpoints

- `GET /api/counterfactual/status`
- `POST /api/counterfactual/run` (token administrativo obrigatorio)

Nenhum resultado autoriza PAPER automatico ou LIVE.
