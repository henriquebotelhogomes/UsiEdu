# Roteiro de Vídeo de Demonstração — UsiEdu

> Conforme doc 04, seção 8 — estratégia de apresentação à empresa (~11 minutos).

---

## 1. Abertura — O problema de negócio (1 min)

**Narração:** "Universidades têm o conhecimento espalhado em dezenas de documentos: regimentos, calendários, manuais e políticas. Estudantes e funcionários perdem horas procurando respostas simples. A UsiEdu unifica esse conhecimento em uma plataforma conversacional multi-agente."

**Tela:** Logo + título "UsiEdu — Assistente Universitário Inteligente".

---

## 2. Demo ao vivo — Os 4 cenários-estrela (3 min)

### 2.1 Cenário composto (US-01) — Ana, estudante
**Pergunta:** "Quero ver minhas notas e o valor do boleto"

**Tela:** Login como Ana Souza → chat → botão "Pergunta composta".

**O que mostrar:**
- Resposta consolidada com notas (Cálculo 1: 5.8, Programação 1: 9.1) e boleto (R$ 890,00 vencido)
- Cards de agentes ("academico", "financeiro") e fontes citadas

### 2.2 Citação institucional (US-02) — Carlos, coordenador
**Pergunta:** "Qual a política de uso dos laboratórios?"

**Tela:** Logout → login como Carlos Oliveira → botão "Política institucional".

**O que mostrar:**
- Resposta com **citação de documento e seção**
- Card de fonte expansível com trecho do documento

### 2.3 Não-alucinação (US-03)
**Pergunta:** "Quais as regras do programa de intercâmbio internacional?"

**O que mostrar:** O agente admite que não encontrou a informação nos documentos oficiais e sugere o canal correto.

### 2.4 Guardrail de escopo (US-04)
**Pergunta:** "Qual a previsão do tempo para amanhã?"

**O que mostrar:** Resposta padrão educada redirecionando ao canal adequado, sem acionar nenhum agente.

---

## 3. Arquitetura (3 min)

**Tela:** Diagrama do doc 01 + tracing real do LangSmith.

**O que mostrar:**
1. Grafo LangGraph: Supervisor → (roteamento) → Agentes → Consolidação
2. Execução paralela no cenário composto (fan-out/fan-in)
3. Trace no LangSmith com run name `usiedu::student::composta`
4. Camada RAG: Qdrant (vetorial) + BM25 + reranker

---

## 4. Qualidade (2 min)

**Tela:** Relatório Ragas + dataset de avaliação.

**O que mostrar:**
- Dataset com 30 perguntas (15 estudante / 15 staff), 5 categorias
- Métricas: faithfulness, context_precision, context_recall, answer_relevancy
- Metas do doc 03 seção 6.1 e status atual
- Como seria avaliação contínua em produção (CI + LangSmith Experiments)

---

## 5. Roadmap (2 min)

**Tela:** Slides de roadmap.

**O que mostrar:**
- Fase 2: Tutor Pedagógico com memória de longo prazo, A2A completo
- Fase 3: MCP servers, multi-tenancy, pipeline contínuo de avaliação
- Visão global do doc 06: escala, segurança de IA, FinOps

---

## Checklist de gravação

- [ ] Ambiente local rodando: `docker compose up` (ou uvicorn + vite)
- [ ] Qdrant com documentos indexados
- [ ] LLM real configurado (OpenCode Go) — respostas em linguagem natural
- [ ] LangSmith com tracing visível
- [ ] Relatório Ragas atualizado
- [ ] 4 cenários testados antes da gravação
- [ ] Ferramenta de gravação (OBS, Loom) configurada
- [ ] Duração total ≤ 11 min
