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
- [ ] Tracing mostra o caminho completo: supervisor → agentes → retriever → LLM.
- [ ] Relatório Ragas com ≥30 perguntas atingindo as metas do doc 03 (seção 5.1).
- [x] `pytest` verde com cobertura ≥ 80% em orquestração/RAG; `ruff check` sem erros. *(validado 06/08/2026 — 206 testes, cobertura 96,7% em orchestration+rag; ruff limpo)*
- [ ] Site MkDocs publicado (GitHub Pages) com toda a documentação navegável.

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
