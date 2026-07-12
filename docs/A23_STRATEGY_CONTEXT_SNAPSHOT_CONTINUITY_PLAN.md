# A23 - Strategy Context Snapshot Continuity Plan

## Objectivo

Preparar o proximo passo depois da A22 sem implementar persistencia nova, mudanca de arquitetura ou qualquer capacidade financeira operacional nesta sessao.

A23 deve continuar observacional, deterministica e fail-closed. Nenhuma opcao abaixo pode gerar decisao, sinal, proposta, risco aprovado, execucao ou trading real.

## Opcao 1 - Historico read-only de snapshots deterministicos

Valor para o projeto:

- Permite auditar a evolucao do contexto A21/A22 ao longo do tempo.
- Ajuda Hermes/Codex a comparar regressao de qualidade sem depender de memoria conversacional.
- Cria base objetiva para troubleshooting e relatorios de continuidade.

Riscos:

- Introduz persistencia nova e precisa de regras claras de retencao.
- Pode crescer em disco se guardar payloads completos sem limite.
- Pode confundir historico observacional com backtesting se a documentacao for fraca.

Persistencia necessaria:

- Tabela SQLite ou ficheiro JSONL dedicado para snapshots aprovados pela A22.
- Chave por fingerprint, versao, fonte, simbolo e timestamp de auditoria.
- Sem segredos, credenciais, precos operacionais ou decisoes.

Impacto em RAM/disco:

- RAM baixa se escrito em streaming.
- Disco baixo/moderado com retencao limitada e deduplicacao por fingerprint.

Compatibilidade com Hermes:

- Alta. Hermes ja trabalha com estados persistentes e pode referenciar fingerprints sem aplicar codigo.
- Deve expor apenas resumos compactos e caminhos, nao payloads enormes.

Seguranca financeira:

- Boa se o contrato continuar sem campos de direcao, ordem, risco aprovado ou execucao.
- Requer guardas para impedir termos operacionais proibidos.

Testes necessarios:

- Persistencia idempotente por fingerprint.
- Retencao e deduplicacao.
- Falha fechada quando A22 falha.
- Nao desbloqueia runtime.
- Smoke permanece bloqueado.

## Opcao 2 - Diff observacional entre snapshots

Valor para o projeto:

- Mostra o que mudou entre dois contextos deterministicos.
- Ajuda a diagnosticar mudancas de fonte, simbolo, qualidade ou estados bloqueantes.
- Pode ser implementado sem persistencia se receber dois snapshots como entrada.

Riscos:

- Pode crescer em complexidade se tentar interpretar impacto das mudancas.
- Pode ser mal entendido como recomendacao se usar linguagem avaliativa.
- Precisa manter whitelist de campos comparaveis.

Persistencia necessaria:

- Nenhuma se a entrada forem dois snapshots fornecidos.
- Opcional no futuro se combinado com a Opcao 1.

Impacto em RAM/disco:

- RAM baixa, proporcional a dois payloads pequenos.
- Disco nulo se sem persistencia.

Compatibilidade com Hermes:

- Alta. Hermes pode pedir diff entre fingerprints ou payloads sem modificar repo.
- Bom para relatorios compactos de progresso.

Seguranca financeira:

- Muito boa se limitar o resultado a alteracoes observacionais e flags bloqueados.
- Nao deve calcular direcao, oportunidade, entrada, saida, tamanho ou risco.

Testes necessarios:

- Diff deterministico e ordenado.
- Campos ausentes reportados como blockers.
- Mudancas em flags criticos geram alerta bloqueante.
- Sem termos operacionais proibidos.
- CLI/endpoint read-only, se expostos.

## Opcao 3 - Research context mock sem capacidade decisoria

Valor para o projeto:

- Poderia preparar um contexto de investigacao mais rico para analise futura.
- Pode agregar notas mock e metadados sem tocar em trading real.

Riscos:

- Maior risco de scope creep para interpretacao de mercado.
- Pode parecer decisorio se incluir linguagem de oportunidade, direcao ou preferencia.
- Exige uma fronteira contratual muito clara para nao enfraquecer fail-closed.

Persistencia necessaria:

- Inicialmente nenhuma, mas research context tende a pedir armazenamento e versionamento.
- Se persistido, deve seguir as mesmas regras de retencao e deduplicacao da Opcao 1.

Impacto em RAM/disco:

- Baixo no mock simples.
- Pode tornar-se moderado se acumular notas ou artefatos de research.

Compatibilidade com Hermes:

- Media. Hermes pode resumir research mock, mas precisa de bloqueios fortes para nao transformar resumo em recomendacao.

Seguranca financeira:

- Media se mal delimitado; boa apenas se todos os outputs forem explicitamente nao decisorios e sem parametros operacionais.

Testes necessarios:

- Guards de linguagem proibida mais rigorosos.
- Flags criticos sempre `false`.
- Nenhuma fonte real, broker, credencial ou LLM em runtime.
- Validacao de que research nao alimenta decisao.

## Recomendacao

Recomendo implementar primeiro a Opcao 2: diff observacional entre dois snapshots A21/A22 fornecidos como entrada.

Motivo:

- Entrega valor diagnostico imediato.
- Nao exige persistencia nova.
- Tem menor impacto arquitetural.
- Mantem compatibilidade forte com Hermes.
- Preserva a arquitetura fail-closed e reduz risco financeiro.

## Sequencia sugerida para A23

1. Definir contrato congelado `StrategyContextSnapshotDiff`.
2. Comparar apenas campos whitelisted de A21/A22.
3. Reportar added/removed/changed como observacao, sem interpretacao financeira.
4. Manter `safe_to_use_for_decision=false`, `decision_generated=false`, `trade_proposal_generated=false`, `risk_approved=false`, `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.
5. Adicionar testes de determinismo, campos ausentes, flags criticos e guards.
6. Adiar persistencia historica para A24 ou para uma A23.2 com aprovacao humana explicita.

## Acoes que exigem aprovacao humana

- Qualquer persistencia nova de historico.
- Qualquer endpoint ou CLI que leia ficheiros fora do runtime mock/test.
- Qualquer integracao com Hermes que gere planos automaticos.
- Qualquer mudanca que aproxime research de decisao financeira.
