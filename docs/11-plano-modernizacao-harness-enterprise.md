# 🚀 Plano Estratégico de Elevação Arquitetural — Padrão Enterprise Harness

> **Documento Normativo e Plano Diretor de Modernização.**  
> Alinhamento do ecossistema **UsiEdu** com as **Diretrizes Globais de Engenharia & Governança (Harness Antigravity)** e o **Inventário de Recursos de IA (resources.md)**.  
> **Status:** Proposto / Blueprint Arquitetural para Implementação Faseada.

---

## Executive Summary

O **UsiEdu** consolidou com sucesso uma arquitetura de referência multi-agente baseada em **LangGraph**, **RAG Híbrido em 4 estágios** (Qdrant + BM25 + Cross-Encoder + CRAG), **FastAPI**, **React 18** e **Azure Container Apps**, respaldada por mais de 540 testes unitários automatizados.

Com a atualização recente das **Diretrizes Globais de Engenharia (Harness)** e a disponibilidade de novos ativos tecnológicos corporativos (Decision Models dedicados como **Jev**, **Gemini 3.8 Flash**, **Datadog Pro via GitHub Student**, **Promptfoo Red-Teaming**, **Scalar Docs**, **DuckDB**, **LanceDB**, **DSPy**, **Cerbos ReBAC** e **xyflow/React Flow**), este documento estabelece o roadmap cirúrgico para elevar a maturidade do projeto ao nível **Série B / Global Scale-up / Big Tech**.

---

## 📊 Matriz de Maturidade: Baseline Atual vs. Alvo Enterprise

| Dimensão Arquitetural | Estado Atual (Baseline UsiEdu) | Estado Alvo (Harness Enterprise) | Ganho Estratégico & FinOps |
|---|---|---|---|
| **Roteamento & Decisão** | LLM de chat generativo (`deepseek-v4-flash`) com JSON | **Jev (`typesafe/jev-latest`)** via OpenRouter | Latência de roteamento de ~800ms para **<30ms**; custo de output **\$0.00** |
| **CRAG Grader** | Corte numérico fixo de threshold de re-ranking (0.05) | **Jev `Noul` / `Score`** com julgamento semântico calibrado | Elimina alucinações de contexto; avaliação em tempo real (<30ms) |
| **Provedores de LLM** | OpenCode Go fixo e stub simulado de Gemini | **Gemini 3.8 Flash** primário + OpenCode Go + Fallback OpenRouter | Throughput massivo com **custo zero** dentro da assinatura Gemini Pro |
| **AI Gateway & Cache** | Semantic Cache em SQLite local | **LiteLLM Proxy / Portkey** com cache semântico compartilhado | Redução de até 40% em tokens e limites de cota por perfil |
| **Documentação da API** | Swagger UI clássico padrão do FastAPI | **Scalar** moderno em `/docs` | UX contemporânea padrão Stripe/GitHub, temas e playground |
| **APM & Observabilidade** | Apenas LangSmith para spans de IA | **Datadog Pro (GitHub Student)** + **Langfuse** + **Sentry** | APM completo de infraestrutura, hosts, erros e telemetria de LLM |
| **Diagnóstico de RAG** | Análises pontuais de slices no Ragas | **Arize Phoenix** com projeção UMAP 2D/3D dos embeddings | Identificação visual de buracos na base de conhecimento |
| **Red-Teaming & Segurança** | Testes de regex/heurística de PII em pytest | **Promptfoo** obrigatório no CI/CD + **NeMo Guardrails** | Pentest contínuo contra jailbreaks, DAN e vazamento de dados |
| **Otimização de Prompts** | Prompts manuais estáticos em strings | **DSPy** (Compilação algorítmica de few-shots via MIPROv2) | Otimização baseada em métricas eliminando tentativa e erro |
| **Analytics & OLAP** | Consultas diretas em SQLite/PostgreSQL | **DuckDB** sobre arquivos colunares `.parquet` | Consultas analíticas ultrarrápidas de feedbacks e telemetria |
| **Vector Store Serverless** | Qdrant em container Docker obrigatório | **LanceDB** embutido / serverless em disco | Zero infraestrutura pesada para testes locais e CI/CD |
| **Frontend & UI/UX** | React 18 com Tailwind puro e sem virtualização | **Shadcn UI** + **TanStack Virtual** + **xyflow (React Flow)** | Visualização interativa do grafo de agentes em tempo real |
| **Autorização & RBAC** | Verificação procedural no código (`student`/`staff`) | **Cerbos (ReBAC / Zanzibar desacoplado)** | Políticas de acesso declarativas em YAML auditáveis |

---

## 🏛️ Os 9 Pilares de Modernização Técnica

```mermaid
graph TD
    subgraph ClientLayer["1. Camada de Apresentação & UI"]
        UI[React 19 + Vite]
        XyFlow[xyflow / React Flow - Grafo Interativo]
        Virtual[TanStack Virtual - DOM Virtualization]
        Shadcn[Shadcn UI + Recharts]
    end

    subgraph GatewayLayer["2. Gateway & Documentação"]
        Scalar[Scalar API Docs /docs]
        FastAPI[FastAPI Lifespan Async]
        AI_GW[LiteLLM Proxy / AI Gateway]
    end

    subgraph DecisionLayer["3. Decision Models & Roteamento (Tier 0)"]
        JevSupervisor["Jev Choice - Supervisor (<30ms, $0.00 output)"]
        JevGrader["Jev Noul - CRAG Grader Documental"]
        JevGuard["Jev Noul - Guardrail Pré-Execução"]
    end

    subgraph LLMLayer["4. Geração & Raciocínio (Tier 1 a 3)"]
        GeminiFlash["Gemini 3.8 Flash (Assinatura Gemini Pro - Custo $0)"]
        OpenCode["OpenCode Go (DeepSeek V4.1 / Kimi K2.7)"]
        OpenRouter["OpenRouter (:free Fallback & Evals)"]
    end

    subgraph DataRAGLayer["5. Armazenamento, OLAP & RAG"]
        Qdrant[Qdrant Hybrid Search]
        LanceDB[LanceDB Serverless / Disco]
        DuckDB[DuckDB OLAP Analytics .parquet]
        Postgres[PostgreSQL + pgvector + RLS]
    end

    subgraph ObservabilityLayer["6. Observabilidade & Segurança"]
        Datadog[Datadog Pro APM - Student Pack]
        Sentry[Sentry Crash Reporting]
        Langfuse[Langfuse LLM APM & Prompt CMS]
        Phoenix[Arize Phoenix UMAP RAG Explorer]
        Promptfoo[Promptfoo CI Red-Teaming Gate]
    end

    UI --> GatewayLayer
    GatewayLayer --> DecisionLayer
    DecisionLayer --> LLMLayer
    LLMLayer --> DataRAGLayer
    GatewayLayer -.-> ObservabilityLayer
```

---

### Pilar 1: Roteamento & Decision Models com Jev (`typesafe/jev-latest`)

#### Problema Atual:
O supervisor do LangGraph (`src/orchestration/supervisor.py`) invoca um modelo generativo completo (`deepseek-v4-flash`), aguardando a geração de tokens de texto com formatação JSON para decidir se a pergunta vai para o agente acadêmico ou financeiro. Isso consome tokens pagos e adiciona latência desnecessária (400ms a 1.200ms).

#### Solução Proposta:
Integrar o modelo **Jev (TypeSafe AI)** via OpenRouter (`typesafe/jev-latest`):
- **Pricing:** \$0.042 por 1 milhão de input tokens | **\$0.00 de output tokens**.
- **Latência:** Sub-30ms com execução determinística tipo System One.
- **Implementações Específicas:**
  1. **Supervisor Router (`Choice`):** Classificação do intent entre `['academico', 'financeiro', 'documental', 'composta', 'fora_de_escopo']`.
  2. **CRAG Retrieval Grader (`Noul`):** Avaliação de cada chunk recuperado pelo RRF/Cross-Encoder com resposta booleana direta (relevante: sim/não) e calibração de probabilidade.
  3. **Guardrail de Entrada (`Noul`):** Detecção instantânea de jailbreak, evasão de prompt e mensagens fora de escopo antes de tocar o grafo.

---

### Pilar 2: Integração do Gemini 3.8 Flash & AI Gateway

#### Problema Atual:
O UsiEdu depende exclusivamente das credenciais do OpenCode Go. O módulo `src/llm/provider.py` possui apenas um stub simulado para Gemini.

#### Solução Proposta:
1. **Gemini 3.8 Flash Nativo:**
   - Adicionar o conector oficial via `google-genai` / `langchain-google-genai` utilizando a chave de assinatura ativa do usuário.
   - Atribuir o **Gemini 3.8 Flash** como motor primário de geração e síntese cognitiva (`consolidation.py` e agentes especialistas), garantindo velocidade extrema, janela de 1M de tokens e custo zero dentro da assinatura.
2. **AI Gateway com LiteLLM Proxy:**
   - Camada agnóstica de roteamento com fallback automático:
     $$\text{Gemini 3.8 Flash (Ativo)} \longrightarrow \text{DeepSeek V4.1 (OpenCode Go)} \longrightarrow \text{Llama-3.3-70B:free (OpenRouter)}$$
   - Cache semântico centralizado com deduplicação de queries de alto volume.

---

### Pilar 3: Interface de Documentação da API com Scalar

#### Problema Atual:
A documentação interativa em `/docs` utiliza o Swagger UI tradicional, que possui design desatualizado e experiência limitada de navegação.

#### Solução Proposta:
Conforme a regra obrigatória do Harness (*"Scalar obrigatório em /docs ou /api/docs. Proibido Swagger UI clássico."*):
- Integrar `scalar-fastapi` no `create_app()` em `src/api/main.py`.
- Apresentar interface moderna com tema dark/light, busca full-text nas rotas da API, visualização refinada de modelos Pydantic e cliente HTTP embutido para testes de endpoints de streaming SSE.

---

### Pilar 4: Observabilidade Enterprise (Datadog + Langfuse + Arize Phoenix + Sentry)

#### Problema Atual:
A observabilidade está restrita ao LangSmith e logs básicos de terminal. Não há métricas de CPU/memória da infraestrutura de containers nem análise visual de qualidade dos embeddings do RAG.

#### Solução Proposta:
1. **Datadog Pro (GitHub Student Developer Pack Ativo):**
   - Instrumentação com `ddtrace-run` ou middleware Datadog FastAPI.
   - Tracing distribuído ponta a ponta: do clique no frontend, passando pela API, até a consulta no Qdrant e inferência no LLM.
   - Dashboards de produção: p50/p95/p99 de latência, vazão de requests por minuto (RPM) e status dos containers no Azure Container Apps.
2. **Sentry for Education (Ativo via Student Pack):**
   - Monitoramento de falhas, exceções não tratadas e timeouts de rede com contexto completo do usuário e stack trace enriquecido.
3. **Langfuse:**
   - APM dedicado a IA: monitoramento de custos por estudante/servidor, rastreamento de nós do LangGraph e Prompt CMS para versionar prompts fora do código-fonte.
4. **Arize Phoenix:**
   - Diagnóstico profundo de RAG: mapa UMAP interativo dos 830 chunks da UnB/MEC para inspecionar agrupamentos temáticos e detectar áreas sem cobertura informacional.

---

### Pilar 5: Red-Teaming Contínuo com Promptfoo em CI/CD

#### Problema Atual:
Os guardrails de segurança dependem de checagens pontuais e estáticas em testes unitários. Não há validação automatizada contra técnicas modernas de evasão de LLMs.

#### Solução Proposta:
1. **Pipeline de Pentest no GitHub Actions (`.github/workflows/security-redteam.yml`):**
   - Execução automatizada do **Promptfoo** em cada Pull Request ou semanalmente.
2. **Casos de Teste Adversários Obrigatórios:**
   - **Jailbreaks:** Ataques estruturados de engenharia reversa (DAN, Universal Adversarial Triggers).
   - **Vazamento de PII:** Tentativas de induzir o modelo a expor CPFs, dados bancários ou registros funcionais simulados.
   - **Injeção Indireta:** Avaliação da resposta do RAG quando documentos da base contêm payloads ocultos de injeção de instruções.
   - **Quality Gate:** Bloqueio obrigatório de merge caso a taxa de sucesso de ataques seja $> 0\%$.

---

### Pilar 6: Compilação e Otimização de Prompts com DSPy

#### Problema Atual:
Os system prompts dos agentes acadêmico, financeiro, institucional e supervisor são estáticos, calibrados manualmente por intuição (*prompt craft*).

#### Solução Proposta:
1. **Módulo DSPy Teleprompter (`scripts/optimize_prompts_dspy.py`):**
   - Modelar a orquestração do UsiEdu com `dspy.Module`.
   - Utilizar o compilador `dspy.MIPROv2` (Multi-prompt Instruction Proposal and Optimization) orientado pelas métricas do Ragas (*Faithfulness* e *Answer Relevance*) e pelo conjunto de dados `dataset.jsonl`.
2. **Resultado Automatizado:**
   - O DSPy gera automaticamente as instruções mais eficientes e os melhores exemplos *few-shot* para cada agente, superando prompts manuais em até 25% de precisão e reduzindo o consumo de tokens.

---

### Pilar 7: Camada Analítica com DuckDB & Vetores com LanceDB

#### Problema Atual:
Consultas analíticas sobre feedbacks, notas de satisfação e dados históricos concorrem com o banco de transações principal ou exigem processamento lento em memória. O Qdrant exige um container Docker rodando localmente.

#### Solução Proposta:
1. **DuckDB para Telemetria e FinOps:**
   - Módulo analítico embutido (`src/analytics/duckdb_engine.py`) operando diretamente sobre arquivos particionados `.parquet`.
   - Consultas SQL OLAP instantâneas: agregações de feedbacks 👍/👎 por agente, cálculo de tempo de resposta por horário e relatórios de custo de tokens por categoria.
2. **LanceDB como Backend Serverless de Vetores:**
   - Integração opcional do LanceDB para ambientes locais, CI/CD e testes rápidos:
     - Armazenamento de vetores em arquivos locais no disco (sem necessidade de subir container Qdrant).
     - Busca vetorial com aceleração SIMD nativa e suporte a metadados colunares.

---

### Pilar 8: Frontend com xyflow (React Flow), Shadcn UI e TanStack Virtual

#### Problema Atual:
O frontend exibe apenas o chat textual e um painel de insights estático. O usuário e os avaliadores não conseguem visualizar a execução do grafo de agentes acontecendo em tempo real.

#### Solução Proposta:
1. **Live Agent Graph com xyflow (React Flow):**
   - Painel interativo demonstrando a topologia visual do LangGraph:
     `[Input] ➔ [Guardrails] ➔ [Supervisor] ➔ [Especialistas Paralelos] ➔ [CRAG Grader] ➔ [Consolidação]`
   - Conexão direta com o stream SSE (`astream_events`): os nós visitados acendem dinamicamente à medida que os eventos chegam da API, proporcionando uma demonstração visual de alto impacto.
2. **DOM Virtualization com TanStack Virtual:**
   - Renderização fluida de conversas com centenas de mensagens e tabelas densas de histórico de feedback sem degradação de performance.
3. **Design System com Shadcn UI & Tailwind:**
   - Componentes acessíveis (Radix UI), modais elegantes de aprovação para Human-in-the-Loop (HITL) e dashboards refinados com Recharts.

---

### Pilar 9: Governança Granular com Cerbos (ReBAC / Zanzibar)

#### Problema Atual:
A autorização de acesso a informações restritas (ex: dados funcionais de servidores, relatórios do DGP) é resolvida com condicionais procedurais simples no código Python.

#### Solução Proposta:
- Implementar **Cerbos**:
  - Políticas de autorização desacopladas em arquivos YAML declarativos (`cerbos/policies/`).
  - Definição formal de permissões baseadas em relacionamento e contexto (ex.: estudante só visualiza seus próprios dados; coordenador de curso acessa turmas do seu departamento; staff do DGP acessa processos específicos com auditoria).

---

## 📅 Roadmap de Implementação em 4 Fases

```mermaid
flowchart LR
    F1[Fase 1: Quick Wins & FinOps\n- Scalar Docs\n- Gemini 3.8 Flash\n- Jev Roteamento & CRAG]
    F2[Fase 2: Observabilidade & DevSecOps\n- Datadog Pro APM\n- Sentry Errors\n- Promptfoo CI Red-Teaming]
    F3[Fase 3: Inteligência & Dados\n- DSPy Prompt Optimization\n- DuckDB Analytics Parquet\n- LanceDB Serverless Adapter]
    F4[Fase 4: Experiência & Governança\n- xyflow Live Agent Graph\n- TanStack Virtual\n- Cerbos ReBAC Policies]

    F1 --> F2 --> F3 --> F4
```

| Fase | Escopo Principal | Esforço Estimado | Entregáveis Técnicos |
|---|---|:---:|---|
| **Fase 1** | **Quick Wins, FinOps & Decision Models** | 1 a 2 dias | • Substituir Swagger UI por **Scalar**<br/>• Conectar **Gemini 3.8 Flash** no provider<br/>• Integrar **Jev (`typesafe/jev-latest`)** no Supervisor e no CRAG Grader |
| **Fase 2** | **Observabilidade Enterprise & Red-Teaming** | 2 a 3 dias | • Ativar **Datadog Pro** e **Sentry** na API<br/>• Quality Gate do **Promptfoo** no GitHub Actions contra jailbreaks<br/>• Configurar **Langfuse** para APM de LLM |
| **Fase 3** | **Otimização de Prompts & Analytics OLAP** | 2 a 3 dias | • Compilação algorítmica de prompts com **DSPy**<br/>• Engine analítico **DuckDB** sobre arquivos `.parquet`<br/>• Adapter vetorial **LanceDB** serverless |
| **Fase 4** | **Experiência Visual Interativa & ReBAC** | 3 a 4 dias | • Componente interativo **xyflow (Live Agent Graph)** no frontend<br/>• **TanStack Virtual** em listas densas<br/>• Políticas declarativas de autorização com **Cerbos** |

---

## Conclusão

A execução deste plano posiciona o **UsiEdu** no topo absoluto dos ecossistemas multi-agente de código aberto, combinando o que há de mais avançado em **Modelos de Decisão (Jev)**, **FinOps Inteligente (Gemini 3.8 Flash + Gateway)**, **DevSecOps rigoroso (Promptfoo)**, **Observabilidade corporativa (Datadog Pro)** e **Experiência do Usuário imersiva (xyflow)**.
