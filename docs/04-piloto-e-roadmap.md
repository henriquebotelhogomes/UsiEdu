# Escopo do Piloto e Roadmap

> Define exatamente o que será construído e enviado à Cruzeiro do Sul,
> critérios de aceite, cronograma sugerido e riscos.

---

## 1. O que será entregue

| # | Entregável | Formato |
|---|---|---|
| 1 | Documentação de arquitetura completa | Site MkDocs (Material) gerado a partir de `docs/` |
| 2 | Aplicação funcional (fatia vertical) | Código-fonte + Docker Compose |
| 3 | Suíte de testes + qualidade | pytest (unitários/integração) + Ruff passando no CI |
| 4 | Dataset de avaliação + relatório Ragas | Scripts + resultados em Markdown |
| 5 | Vídeo de demonstração (~5 min) | Roteiro guiado pela arquitetura |
| 6 | Roadmap de evolução | Seção 3 deste documento |

## 2. Fatia vertical do piloto (dentro/fora)

### ✅ Dentro do escopo

**Estudante:**
- Supervisor com classificação de intenção e guardrails.
- Agente Acadêmico: RAG (regimento/calendário sintéticos) + 2 tools mockadas (`get_notas`, `get_faltas`).
- Agente Financeiro: 2 tools mockadas (`get_boletos`, `simular_renegociacao`).
- **Cenário-estrela**: pergunta composta resolvida pelos dois agentes em colaboração.

**Funcionário:**
- Supervisor compartilhado.
- Agente Documental: RAG híbrido com citação de fonte sobre políticas sintéticas.

**Infraestrutura:**
- FastAPI com autenticação simples por perfil (JWT).
- Frontend **React + Vite (TypeScript)**: chat com exibição de fontes citadas e do agente que respondeu.
- Pipeline de ingestão + Qdrant (2 coleções).
- Checkpointer SQLite (memória de sessão).
- Tracing de LLM (LangSmith, free tier).
- Qualidade: Ruff + pytest com cobertura; documentação navegável via MkDocs.

### ❌ Fora do escopo do piloto (roadmap)

- Tutor Pedagógico com memória de longo prazo (Store persistente).
- Agente de Carreira e Agente de Processos + MCP server.
- Protocolo A2A completo entre agentes (piloto usa delegação in-process).
- Grafana/Prometheus completos (avaliar — ver decisões em aberto).
- Integração com sistemas reais da instituição.

## 3. Roadmap pós-piloto

### 3.1 Plano de melhoria das métricas Ragas (prioridade imediata)

Fechamento honesto do critério 7: o pipeline RAG funciona (contexto recuperado e citado),
mas as metas do doc 03 (seção 6.1) não foram atingidas no agregado. Plano de convergência:

1. **Corrigir a régua de medição**: excluir `fora_de_escopo` do agregado Ragas (guardrail
   RF-10 não é mensurável por faithfulness/relevancy) e avaliar essa categoria com
   LLM-as-judge próprio (assertiva de redirecionamento).
2. **Fechar a lacuna de corpus staff**: indexar a Lei 8.112/90 completa e revisar o Guia
   do Servidor — 5 perguntas (q018–q022) zeraram por ausência de conteúdo, não por falha
   de recuperação.
3. **Fortalecer o juiz**: reavaliar o dataset com um LLM juiz mais forte (avaliação é mais
   confiável que geração com modelo econômico) e comparar estabilidade dos scores.
4. **Iterar pipeline e medir regressão**: ajustes de prompts de agentes e reranking,
   rodando o dataset como experimento no LangSmith a cada mudança.
5. **Laço de feedback negativo (T8.1)**: cada 👎 vira caso de regressão automático —
   `python scripts/export_feedback_to_eval.py` exporta os 👎 do banco de feedback para
   `src/evaluation/feedback_negativo.jsonl` (idempotente por `message_id`; pergunta e
   resposta rejeitada recuperadas do checkpointer da sessão; sem checkpoint, exporta com
   `question: null`). O `run_ragas.py` reexecuta esses casos e o relatório ganha a seção
   "Casos de feedback negativo", comparando a nova resposta com a rejeitada (heurística
   Jaccard offline; em modo Ragas+LLM recomenda-se confirmar com LLM judge). Casos com
   `question: null` são contabilizados como pulados.

### Fase 2 — Expansão de agentes (+4 semanas)
1. Tutor Pedagógico com memória de longo prazo e quizzes adaptativos.
2. Agente de Carreira.
3. Agente de Processos + `processos-mcp` (MCP server real).
4. Grafana + Prometheus com dashboards de latência/tokens.

### Fase 3 — Plataforma e produção (+6 semanas)
1. Migração para protocolo **A2A**: cada agente vira serviço independente com Agent Card.
2. Avaliação contínua em produção (amostragem de conversas + LLM-as-judge).
3. Otimização de tokenomics: cache semântico, sumarização agressiva, modelos menores para roteamento.
4. Implantação em Kubernetes/Rancher com autoscaling.

## 4. Cronograma sugerido do piloto

| Semana | Foco | Resultado esperado |
|---|---|---|
| 1 | Fundação | FastAPI + grafo LangGraph com Supervisor + 1 agente RAG funcionando |
| 2 | Multi-agente | Agente Financeiro + cenário composto + tools mockadas |
| 3 | Qualidade | Perfil funcionário, busca híbrida + reranking, dataset Ragas |
| 4 | Acabamento | Tracing, interface web, vídeo de demo, revisão final |

> Dedicando ~10–15h/semana: ~4 semanas. Dedicando mais horas, comprimível para 2–3 semanas.

## 5. Critérios de aceite do piloto

- [x] Estudante pergunta algo composto (acadêmico+financeiro) e recebe resposta consolidada com fontes. *(validado 06/08/2026 — `scripts/test_aceite.py` C1)*
- [x] Funcionário pergunta norma institucional e recebe resposta **com citação** de documento/seção. *(validado 06/08/2026 — `scripts/test_aceite.py` C2, Guia do Servidor)*
- [x] Pergunta sem resposta nos documentos → agente admite não saber (não alucina). *(validado 06/08/2026 — pergunta sobre laboratórios respondida com honestidade)*
- [x] Pergunta fora de escopo → resposta educada de redirecionamento. *(validado 06/08/2026 — nó `fora_de_escopo` RF-10)*
- [x] Conversa mantém contexto entre turnos (checkpointer). *(validado 06/08/2026 — `scripts/test_aceite.py` C5, mesmo thread_id)*
- [x] Tracing mostra o caminho completo: supervisor → agentes → retriever → LLM. *(validado 07/08/2026 — projeto `usiedu-pilot` no LangSmith: LangGraph → supervisor → ChatOpenAI → route_from_supervisor → academico → ChatOpenAI → consolidation; contexto RAG presente no run do agente; `scripts/verify_tracing.py`)*
- [~] Relatório Ragas com ≥30 perguntas atingindo as metas do doc 03 (seção 5.1). *(parcialmente validado 07/08/2026 — 30 perguntas avaliadas com Ragas+LLM; metas não atingidas no agregado: faithfulness 0,565, context precision/recall 0,645, answer relevancy 0,565 vs metas 0,90/0,80/0,80/0,85. Causas: artefato de medição nas 4 perguntas fora_de_escopo (comportamento correto RF-10 pontua 0), lacuna de corpus staff em q018–q022 e juiz LLM de baixo custo. `sem_resposta` = 1,000 em tudo. Leitura crítica e plano de melhoria: seção 3.1 e `src/evaluation/relatorio_ragas.md`)*
- [x] `pytest` verde com cobertura ≥ 80% em orquestração/RAG; `ruff check` sem erros. *(validado 06/08/2026 — 206 testes, cobertura 96,7% em orchestration+rag; ruff limpo)*
- [x] Site MkDocs publicado (GitHub Pages) com toda a documentação navegável. *(validado 07/08/2026 — https://henriquebotelhogomes.github.io/UsiEdu/, republicação automática via `.github/workflows/docs.yml`)*
- [~] Visitante anônimo usa landing, login demo, chat, feedback e `/insights` por HTTPS. *(artefatos Azure Container Apps preparados em T9.4; validação aguarda primeiro provisionamento público.)*

## 6. Base de conhecimento do piloto (fontes abertas reais)

A base de conhecimento usa documentos reais e públicos de **uma única instituição** (UnB),
garantindo consistência das regras, mais legislação federal como camada multinível.
Catálogo completo com links em `05-fontes-base-conhecimento.md`:

| Categoria | Fonte |
|---|---|
| Estatuto + Regimento Geral | UnB |
| Calendários acadêmicos 2026.1/2026.2 + calendário de matrícula | UnB (SAA) |
| Guia do calouro | UnB |
| Guia do servidor | UnB (DGP) |
| Legislação | LDB (Lei 9.394/96), Lei 8.112/90 |

> Na apresentação, deixar explícito que a UnB é usada como stand-in de uma instituição real —
> mesma engenharia e mesma dificuldade de uma base proprietária.

## 7. Riscos e mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Escopo inflar durante o desenvolvimento | Atraso/não entrega | Checklist desta seção como contrato; itens fora vão para roadmap |
| Custo de API no piloto | Custo inesperado | Motor 100% via OpenCode Go (assinatura já paga, custo zero adicional); embeddings e reranker locais |
| Qdrant pesado para demo | Atrito para avaliador rodar | Docker Compose único; fallback: modo "tudo embutido" com Qdrant em memória |
| RAG ruim por documentos fracos | Métricas baixas | Usar documentos reais da UnB (doc 05), densos em regras testáveis |
| Avaliador não rodar o código | Esforço desperdiçado | Vídeo de demo cobrindo todos os critérios de aceite |

## 8. Estratégia de apresentação à empresa

1. **Abertura (1 min)**: problema de negócio (atendimento fragmentado + conhecimento disperso) e visão da plataforma unificada.
2. **Demo ao vivo (3 min)**: os 4 critérios-estrela (composto, citação, não-alucinação, fora de escopo).
3. **Arquitetura (3 min)**: diagrama do doc 01 + tracing real do LangSmith mostrando a orquestração.
4. **Qualidade (2 min)**: relatório Ragas + como seria avaliação contínua em produção.
5. **Roadmap (2 min)**: Fases 2 e 3 — Tutor com memória, A2A completo, MCP — mostrando visão de longo prazo.

---

## 9. Decisões finais necessárias *(para revisão)*

- [ ] Data-alvo de envio da candidatura.

**Decisões já fechadas:**
- ✅ Nome do produto: **UsiEdu**.
- ✅ Tracing: **LangSmith**.
- ✅ Base de conhecimento: **documentos reais da UnB** (instituição única, sem regras conflitantes) + legislação federal — ver doc 05.
- ✅ Modelos: Gemini **fora** do piloto; motor 100% OpenCode Go, com suporte a Gemini documentado na camada provider-agnostic.
