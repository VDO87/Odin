# Risk Policy

O Risk Engine e autoridade superior para risco operacional e financeiro.

Politicas:

- Estado inicial: bloqueado para real.
- Falta de configuracao de risco implica bloqueio.
- Falta de logs auditaveis implica bloqueio.
- Qualquer tentativa de execucao real sem aprovacao implica bloqueio.
- Hermes nao pode reduzir, contornar ou aprovar risco.
- Dashboard deve reflectir bloqueios de risco sem suavizar linguagem.
- A9 Decision Intent nao aprova risco: `risk_approved=false` por desenho.
- A10 Risk Gate bloqueia tudo por defeito: `risk_status=BLOCKED`.
- A11 Shadow Proposal depende do Risk Gate e permanece bloqueada quando o risco esta bloqueado.
