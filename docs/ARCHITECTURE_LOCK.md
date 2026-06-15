# Architecture Lock

ODIN_HERMES_ALIVE arranca na fase A0 - Bootstrap. A arquitectura fica separada por responsabilidades:

- Core: orquestracao operacional e estado.
- Risk: limites, bloqueios e validacao de seguranca financeira.
- Treasury: capital, liquidez, fiscalidade operacional e regras de dinheiro.
- Hermes: camada cognitiva read-only para memoria, RAG, relatorios e recomendacoes.
- Dashboard: cockpit humano para auditoria, logs e decisao assistida.
- Adapters: integracoes externas isoladas.

Bloqueios estruturais:

- Trading real esta bloqueado por defeito.
- `mt5.order_send` e proibido.
- XTB nao pode ser automatizado para clicar ou enviar ordens.
- Hermes nao aprova nem executa operacoes.
- Risk vence sempre Hermes.
- Treasury vence sempre Hermes em materia de dinheiro.
