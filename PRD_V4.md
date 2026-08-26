# PRD v4 — UsiEdu: Escala Enterprise & Hiper-Automação (Padrão Série B / Big Tech)

> **Documento de Especificação Técnica e Arquitetural v4.**
> Focado na evolução para alta escala, governança avançada, aprovação humana no fluxo (*Human-in-the-Loop Interrupts*), segurança com guardrails em camadas e automação de CI/CD para qualidade de IA.

---

## 1. Objetivo da Versão v4

Expandir a plataforma **UsiEdu** para além da fundação multi-agente estabelecida na v3, implementando recursos de **Série B / Scale-up Global**:
1. **Controle e Governança:** Aprovação humana em ações críticas (*Human-in-the-Loop* com interrupção de grafo no LangGraph).
2. **Segurança e Moderação:** Camada de guardrails semânticos e neurais para proteção contra injeções complexas e vazamento de PII.
3. **Qualidade Contínua (CI/CD Quality Gates):** Pipeline de integração contínua que bloqueia deploys se as métricas do RAGAS caírem abaixo das metas.
4. **Escalabilidade Distribuída:** Abstração de cache semântico e rate limiting compatível com Redis para clusters com múltiplas instâncias.
5. **Experiência do Usuário (UX & Rich UI):** Renderização avançada de Markdown com tabelas interativas, blocos de código copiáveis e visualização refinada de fontes.

---

## 2. Requisitos Funcionais da Versão v4 (RF4-xx)

### 2.1 Governança e Human-in-the-Loop
- **RF4-01 (LangGraph Human-in-the-Loop Interrupt):** Integrar o mecanismo de `interrupt_before` do LangGraph em nós de ações financeiras ou cadastrais sensíveis (ex.: confirmação formal de proposta de renegociação). O grafo suspende a execução e só conclui após aprovação explícita via endpoint `POST /chat/resume`.

### 2.2 Segurança e Guardrails em Camadas
- **RF4-02 (Multi-Layer AI Guardrails):** Evoluir o módulo de guardrails para arquitetura em duas camadas:
  1. *Camada Rápida (Heurística & Regex):* Bloqueio instantâneo de padrões conhecidos de SQLi, XSS e jailbreaks comuns.
  2. *Camada Semântica/Neural:* Validação contextual de toxicidade, intenções maliciosas veladas e detecção estrita de PII (CPF, dados bancários e senhas).

### 2.3 Qualidade e CI/CD Automatizado
- **RF4-03 (Automated RAGAS Quality Gate):** Criar workflow de CI/CD (GitHub Actions) executando `scripts/run_ragas.py` como teste de regressão de qualidade. Se *Faithfulness* < 0.85 ou *Answer Relevancy* < 0.85, a build falha automaticamente.

### 2.4 Escalabilidade Distribuída
- **RF4-04 (Distributed Cache & Rate Limiting Provider):** Criar adapter de cache e controle de taxa com chave de configuração `USIEDU_STORAGE_BACKEND` (`sqlite` para ambientes leves/locais e `redis` para clusters distribuídos de alta concorrência).

### 2.5 Frontend e Rich Chat UX
- **RF4-05 (Rich Markdown & Source Navigation):** Implementar no frontend React renderizador Markdown com suporte a blocos de código com botão de cópia, tabelas estilizadas, badges de status para agentes e gaveta retrátil (*drawer*) para leitura integral de fontes citadas.

---

## 3. Matriz de Componentes Afetados (v4)

| Componente | Arquivo / Módulo | Natureza da Alteração |
|---|---|---|
| **Orquestração HITL** | `src/orchestration/graph.py`<br>`src/api/chat.py` | Suporte a `interrupt_before` e endpoint de aprovação |
| **Guardrails Avançados** | `src/security/guardrails.py` | Moderação neural e PII mask |
| **CI/CD Quality Gate** | `.github/workflows/quality_gate.yml`<br>`scripts/run_ragas.py` | Flag `--ci-gate` e pipeline automatizada |
| **Storage Distribuído** | `src/rag/cache.py`<br>`src/api/rate_limit.py` | Backend plugável (SQLite / Redis) |
| **Frontend UI/UX** | `frontend/src/components/Markdown.tsx`<br>`frontend/src/components/MessageCard.tsx` | Markdown rico, tabelas e visualizador de fontes |

---

## 4. Checklist Executivo de Implementação e Status (v4)

| ID | Requisito / Atividade | Prioridade | Status | Arquivo Alvo | Evidência de Validação |
| :---: | :--- | :---: | :---: | :--- | :--- |
| **ACT4-01** | Implementar `interrupt_before` no LangGraph para ações financeiras críticas | Alta | ✅ **Concluído** | `src/orchestration/graph.py` | `test_hitl.py` (test_grafo_pausa_no_interrupt_before) |
| **ACT4-02** | Criar endpoint `POST /chat/resume` para aprovação e continuidade de threads pausadas | Alta | ✅ **Concluído** | `src/api/chat.py` | `test_hitl.py` (test_endpoint_resume_retoma_execucao) |
| **ACT4-03** | Adicionar detecção e mascaramento de PII (CPF, RG, e-mails sensíveis) nos guardrails | Média | ✅ **Concluído** | `src/security/guardrails.py` | `test_guardrails.py` (TestMaskPII suite) |
| **ACT4-04** | Criar flag `--ci-gate` no `scripts/run_ragas.py` com exit code 1 se métricas < threshold | Média | ✅ **Concluído** | `scripts/run_ragas.py` | `python scripts/run_ragas.py --ci-gate` |
| **ACT4-05** | Criar workflow `.github/workflows/quality_gate.yml` para validação em PRs | Média | ✅ **Concluído** | `.github/workflows/quality_gate.yml` | Pipeline de CI configurada com lint, unit tests e Ragas gate |
| **ACT4-06** | Adicionar suporte a Redis como backend opcional para Semantic Cache | Média | ✅ **Concluído** | `src/rag/cache.py` | `redis_url()` e conexão comutada dinamicamente |
| **ACT4-07** | Aprimorar renderização de Markdown no Frontend (tabelas, códigos copiáveis, badges) | Baixa | ✅ **Concluído** | `frontend/src/components/Markdown.tsx` | Componente CodeBlock com botão de cópia e styled tables |
