# Auditoria da Update 75

A Update 74 misturava observações de símbolos diferentes na calibração do
Quant Brain, dimensionava a posição pelo stop sem reservar todos os custos e
encerrava o stop PAPER pelo preço observado após o rompimento.

A Update 75 torna o símbolo obrigatório nas estimativas de calibração, calcula
o notional usando stop + slippage + duas taxas, reserva o risco das posições
abertas e usa o preço do stop no fechamento PAPER/Shadow.

Parâmetros PAPER:

- banca inicial nova: R$ 200,00;
- risco líquido por entrada: 2%;
- risco agregado máximo: 10%;
- hard stop: 25%;
- alavancagem máxima: 15x;
- scanner: análise rasa e top 60 profundo.

A atualização não reinicia contas PAPER existentes e não habilita LIVE.
