# Update 57 — RC Verification Harness

## Por que existe

A Update 56 congela a arquitetura. A Update 57 não adiciona lógica de
trading: ela verifica o repositório real depois da aplicação das updates.

## Uso

`python tools/rc_verify.py`

O comando grava:

`reports/rc_verification_report.json`

## Interpretação

`RC_VERIFY_PASS` = estrutura instalada coerente com o Release Candidate.

`RC_VERIFY_FAIL` = corrigir a instalação antes de continuar a coleta de
evidências.

LIVE permanece bloqueado.
