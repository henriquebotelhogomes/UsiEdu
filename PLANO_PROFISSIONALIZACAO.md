# Plano de Profissionalizacao — UsiEdu

> Documento vivo para registrar e detalhar os ajustes que elevam o UsiEdu de
> portfólio técnico e piloto público a uma solução mais próxima de produção.
> Atualizado em 11/08/2026.

## Avaliacao atual

O UsiEdu está em nível profissional para **portfólio técnico** e **piloto
público**, mas ainda não está pronto para operação institucional crítica.

### Pontos fortes já demonstrados

- Arquitetura multiagente com LangGraph.
- RAG híbrido com Qdrant, BM25 e reranker.
- Streaming SSE, histórico de sessão e feedback de respostas.
- Cache semântico, rate limiting e guardrails contra prompt injection.
- PostgreSQL para persistência no piloto público.
- Deploy HTTPS em Azure Container Apps.
- Testes automatizados, Ruff, CI, documentação e avaliação Ragas.

### Critério de evolução

Os próximos trabalhos devem priorizar confiabilidade, operação, segurança e
evidência mensurável de qualidade. Novos agentes ou funcionalidades só entram
quando atenderem uma necessidade registrada no PRD ou backlog.

## Prioridade 0 — Validacao do piloto publicado

- [ ] Validar, na URL pública e após o ajuste de 2 vCPUs/4 GiB, o fluxo
  landing → login demo → chat com RAG → feedback → `/insights`.
- [ ] Registrar evidência de que uma pergunta documental responde sem o
  encerramento do contêiner com código 137.
- [ ] Medir e documentar tempo de cold start, primeira resposta e resposta com
  modelos já aquecidos.
- [ ] Verificar `/health`, logs da API e execução bem-sucedida do job de
  ingestão após um novo deploy.

## Prioridade 1 — Qualidade mensurável do RAG

O último relatório, gerado em 06/08/2026 no modo Ragas+LLM, não atingiu as
metas agregadas:

| Métrica | Atual | Meta |
|---|---:|---:|
| Faithfulness | 0,565 | >= 0,90 |
| Context precision | 0,645 | >= 0,80 |
| Context recall | 0,645 | >= 0,80 |
| Answer relevancy | 0,565 | >= 0,85 |

Diagnóstico já conhecido:

- Perguntas `fora_de_escopo` reduzem artificialmente faithfulness e relevancy,
  embora o redirecionamento seja o comportamento correto.
- Há lacunas reais no corpus institucional de funcionários, especialmente para
  perguntas que exigem normas não indexadas.
- O juiz de avaliação é econômico; um juiz mais robusto pode tornar a medição
  mais estável.

### Próximos ajustes

- [ ] Separar as categorias `fora_de_escopo` e `sem_resposta` do agregado de
  perguntas RAG respondíveis, preservando relatórios específicos para elas.
- [ ] Mapear cada pergunta com nota zero a uma fonte ausente, fonte existente
  mal recuperada ou resposta insuficiente.
- [ ] Ampliar o corpus institucional autorizado e reexecutar a ingestão.
- [ ] Criar um gate de regressão no CI para o dataset de avaliação antes de
  alterar prompt, chunking, embedding ou reranker.
- [ ] Comparar o avaliador econômico com um LLM judge mais forte e registrar
  custo, estabilidade e resultado.

## Prioridade 1 — Integracao, entrega e rollback

O CI atual valida lint, formato e testes unitários. A próxima etapa é cobrir os
limites entre serviços e tornar a entrega repetível.

- [ ] Criar testes de integração para frontend → nginx → API.
- [ ] Criar testes de integração para API → PostgreSQL e API → Qdrant.
- [ ] Criar teste ponta a ponta para login → chat → feedback → `/insights`.
- [ ] Automatizar build, testes e deploy com GitHub Actions.
- [ ] Usar tags de imagem imutáveis derivadas do commit.
- [ ] Definir rollback para a revisão anterior do Container App.
- [ ] Adicionar aprovação explícita antes de deploy público.
- [ ] Adicionar scan de vulnerabilidades das imagens Docker.

## Prioridade 1 — Seguranca e continuidade operacional

- [ ] Migrar segredos para Azure Key Vault e, quando possível, Managed Identity.
- [ ] Impedir geração involuntária de um novo `JWT_SECRET` em cada deploy;
  documentar rotação de chaves e impacto em sessões.
- [ ] Revisar dados pessoais enviados a logs e LangSmith, com política de
  retenção, minimização e anonimização.
- [ ] Definir política de privacidade e requisitos LGPD para um piloto com
  usuários externos.
- [ ] Configurar backup do PostgreSQL e testar restauração.
- [ ] Documentar backup, recuperação e consistência do volume do Qdrant.
- [ ] Criar alerta de orçamento e alertas operacionais para falha de API,
  ingestão e banco.

## Prioridade 2 — Performance e disponibilidade

- [ ] Medir consumo de memória e latência do embedder e reranker no Azure.
- [ ] Ajustar startup, readiness e liveness probes à carga dos modelos locais.
- [ ] Definir limites de timeout, retry e comportamento de falha para chamadas
  ao LLM, Qdrant e PostgreSQL.
- [ ] Avaliar se `minReplicas: 0` é adequado para a demonstração ou se uma
  réplica aquecida justifica o custo.
- [ ] Reduzir tempo de cold start: imagem, cache de modelo, estratégia de
  aquecimento ou modelo mais leve devem ser comparados por custo e latência.

## Prioridade 2 — Produto e experiencia

- [ ] Melhorar a mensagem do chat quando um stream falhar ou for interrompido.
- [ ] Definir política explícita para perguntas genéricas: responder com
  conhecimento geral seguro, usar ferramenta determinística ou redirecionar.
- [ ] Executar revisão de acessibilidade, responsividade mobile e fluxos de
  teclado.
- [ ] Adicionar página de contato e vídeo curto de demonstração ao portfólio.
- [ ] Capturar e incluir screenshot da página `/insights`.

## Definition of Done para cada ajuste

Um item só pode ser marcado como concluído quando:

- [ ] Existe requisito, decisão ou item de backlog que justifique o escopo.
- [ ] Há teste automatizado proporcional ao risco, criado antes da mudança.
- [ ] Ruff e a suíte de testes relevante passam localmente e no CI.
- [ ] Documentação, variáveis de ambiente e runbooks foram atualizados quando
  aplicável.
- [ ] O deploy foi validado sem expor segredo, dado pessoal ou regressão no
  piloto público.

## Referencias

- `PRD.v2.md`
- `docs/03-rag-e-infraestrutura.md`
- `docs/04-piloto-e-roadmap.md`
- `docs/07-prd-requisitos.md`
- `docs/08-plano-execucao.md`
- `docs/09-contratos-tecnicos.md`
- `src/evaluation/relatorio_ragas.md`
