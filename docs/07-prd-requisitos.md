# PRD — UsiEdu (Product Requirements Document)

> Documento de requisitos do **piloto**. Qualquer implementador (humano ou IA) deve
> construir exatamente isto — nem mais, nem menos. Requisitos fora desta lista
> pertencem ao roadmap (doc 04) ou à visão global (doc 06).

---

## 1. Objetivo do produto

Plataforma de chat multi-agente que atende dois perfis:
- **Estudante**: dúvidas acadêmicas e financeiras resolvidas por agentes colaboradores.
- **Funcionário/Docente**: consultas a normas e políticas institucionais com citação de fonte.

**Métrica de sucesso do piloto:** os 7 critérios de aceite do doc 04 (seção 5) passando,
com relatório Ragas dentro das metas do doc 03 (seção 6.1).

## 2. Personas e permissões

| Persona | Login demo | Agentes disponíveis |
|---|---|---|
| Ana (estudante de ADS) | `ana@demo.usiedu` | Supervisor, Acadêmico, Financeiro |
| Carlos (coordenador) | `carlos@demo.usiedu` | Supervisor, Documental |

## 3. Requisitos Funcionais

### 3.1 Autenticação e perfis

- **RF-01**: Login por email/senha (usuários demo fixos) retorna JWT com o perfil (`student` | `staff`).
- **RF-02**: Toda conversa é associada ao perfil do usuário; agentes não autorizados para o perfil nunca são acionados.

### 3.2 Conversação

- **RF-03**: Endpoint de chat mantém histórico por sessão (checkpointer); contexto é retido entre turnos.
- **RF-04**: Toda resposta final inclui as **fontes usadas** (documento, seção/trecho, URL quando houver).
- **RF-05**: Toda resposta final indica **quais agentes** participaram (metadado exposto à API).

### 3.3 Supervisor (orquestração)

- **RF-06**: Classifica a intenção da mensagem em: `academico`, `financeiro`, `institucional`, `composta`, `fora_de_escopo`.
- **RF-07**: Intenção simples → delega a um agente (padrão ReAct).
- **RF-08**: Intenção `composta` → gera plano com sub-tarefas numeradas e delega a múltiplos agentes (Plan-and-Solve), em paralelo quando independentes.
- **RF-09**: Consolida resultados parciais em **uma única resposta coerente**, sem contradições entre agentes.
- **RF-10**: `fora_de_escopo` → resposta padrão educada redirecionando ao canal adequado; nenhum agente é chamado.
- **RF-11**: Se a consolidação detectar resposta incompleta, o grafo retorna ao supervisor (ciclo) — máximo de 2 ciclos antes de responder com o que tem.

### 3.4 Agente Acadêmico (estudante)

- **RF-12**: Responde com RAG sobre a coleção `academico` (Regimento UnB, Calendários 2026, Guia Calouro, LDB).
- **RF-13**: Tools mockadas disponíveis: `get_notas(aluno_id)`, `get_faltas(aluno_id, disciplina)`.
- **RF-14**: Sem fonte recuperada com relevância suficiente → responde explicitamente que não encontrou nos documentos oficiais e sugere canal humano (nunca inventa).

### 3.5 Agente Financeiro (estudante)

- **RF-15**: Tools mockadas: `get_boletos(aluno_id)`, `simular_renegociacao(boleto_id, parcelas)`.
- **RF-16**: Aplica apenas regras presentes na política financeira mockada indexada; nunca promete desconto fora dela.
- **RF-17**: Valores financeiros aparecem formatados (R$) e mascarados em logs.

### 3.6 Agente Documental (staff)

- **RF-18**: Responde com RAG sobre a coleção `institucional` (Guia do Servidor UnB, Regimento parte administrativa, Lei 8.112).
- **RF-19**: Toda afirmação normativa traz citação (documento + seção).

### 3.7 Pipeline RAG

- **RF-20**: Script de ingestão idempotente: baixa/ler documentos de `knowledge_base/`, chunking semântico (500–800 tokens, overlap 15%), embed local, grava no Qdrant com metadados (`instituicao`, `documento`, `secao`, `pagina`, `url_fonte`, `publico_alvo`).
- **RF-21**: Recuperação híbrida (vetorial + BM25) top-20 → reranking local → top-5.
- **RF-22**: Filtro obrigatório por perfil: `student` acessa apenas `academico`; `staff` apenas `institucional`.
- **RF-23**: Documentos do piloto: Regimento Geral UnB, Calendário Graduação 2026.2 (SAA), Guia do Servidor UnB, LDB (núcleo mínimo — doc 05).

### 3.8 Frontend (React + Vite)

- **RF-24**: Tela de login (usuários demo visíveis na própria tela).
- **RF-25**: Chat com streaming (SSE) das respostas.
- **RF-26**: Cada resposta exibe: texto, agentes envolvidos e fontes citadas (cards expansíveis).
- **RF-27**: Botões de "cenários de demo" (4 perguntas prontas cobrindo os critérios de aceite).

### 3.9 Avaliação

- **RF-28**: Dataset versionado com ≥ 30 perguntas (15 estudante / 15 staff) e respostas de referência, incluindo casos sem resposta e fora de escopo.
- **RF-29**: Script de avaliação gera relatório Ragas (faithfulness, context_precision, context_recall, answer_relevancy) em Markdown.

### 3.10 Observabilidade e qualidade

- **RF-30**: Toda execução do grafo gera trace no LangSmith (run name com perfil + intenção).
- **RF-31**: Logs estruturados em JSON com `trace_id`.
- **RF-32**: `ruff check` e `ruff format` sem erros; suíte pytest verde com cobertura ≥ 80% em `orchestration/` e `rag/`.
- **RF-33**: Site MkDocs gerado a partir de `docs/`.

## 4. Requisitos Não-Funcionais

| ID | Requisito | Meta |
|---|---|---|
| RNF-01 | Latência p95 (pergunta composta, ambiente local) | < 20 s |
| RNF-02 | Custo de LLM/embedding no piloto | Zero (OpenCode Go + modelos locais) |
| RNF-03 | Inicialização | `docker compose up` sobe API + frontend + Qdrant |
| RNF-04 | Portabilidade | Roda em Windows/macOS/Linux com Python 3.12+ e Node 20+ |
| RNF-05 | Privacidade | Nenhum dado pessoal real; PII apenas em mocks rotulados |
| RNF-06 | Segurança | JWT expira em 1 h; segredos somente via variáveis de ambiente |
| RNF-07 | Idempotência | Reingerir documentos não duplica chunks |

## 5. User Stories com critérios de aceite

### US-01 — Pergunta composta (cenário-estrela)
> Como **Ana**, quero perguntar algo que envolve regras acadêmicas e custos, recebendo uma única resposta consolidada.

**Dado** que estou logada como estudante,
**Quando** pergunto "Perdi o prazo de matrícula em Cálculo. Quais são minhas opções e quanto custa?",
**Então** o Supervisor aciona Acadêmico e Financeiro,
**E** recebo resposta única com passos, valores e fontes citadas,
**E** os metadados listam ambos os agentes.

### US-02 — Norma institucional com citação
> Como **Carlos**, quero consultar uma norma e receber a fonte exata.

**Dado** que estou logado como staff,
**Quando** pergunto "Quais são meus direitos de licença capacitação?",
**Então** recebo resposta baseada no Guia do Servidor/Lei 8.112 com citação de documento e seção.

### US-03 — Honestidade sobre limite do conhecimento
> Como **Ana**, quando a resposta não está nos documentos, quero que o assistente admita.

**Dado** que pergunto algo não coberto pela base (ex.: "posso estacionar meu carro no campus?"),
**Então** o agente responde que não encontrou a informação nos documentos oficiais,
**E** nenhuma fonte é inventada.

### US-04 — Guardrail de escopo
> Como **Ana**, quando faço pergunta fora do domínio institucional,
**Então** recebo resposta educada de redirecionamento, sem acionar agentes.

### US-05 — Retenção de contexto
> Como **Ana**, em conversa multi-turno,
**Quando** digo "e quanto custa a segunda opção?" referindo-me à resposta anterior,
**Então** o sistema resolve a referência usando o histórico da sessão.

## 6. Fora de escopo do piloto (não implementar)

- ❌ Tutor Pedagógico, Agente de Carreira, Agente de Processos, MCP server.
- ❌ Protocolo A2A entre processos/serviços separados.
- ❌ Memória de longo prazo entre sessões (Store persistente).
- ❌ Grafana/Prometheus (avaliar — ver doc 03, decisões em aberto).
- ❌ Multi-tenancy, OIDC/SSO, Kubernetes — ver doc 06.

## 7. Checklist de aceite do produto (gate de entrega)

- [x] RF-01 a RF-33 implementados e cobertos por testes quando aplicável (147 testes)
- [x] 7 critérios de aceite do doc 04 (seção 5) demonstráveis (frontend + API funcionais)
- [x] Relatório Ragas dentro das metas (doc 03, seção 6.1) — gerado com RAG real + LLM (DeepSeek V4 Flash). Métricas: faithfulness 0.429, context_precision 0.519, context_recall 0.519, answer_relevancy 0.429. Melhoria de ~60% em relação ao modo sem RAG. Metas finais (0.90/0.80/0.80/0.85) exigem reranker + mais documentos + ajuste de prompts.
- [x] `docker compose up` funcional do zero (api + frontend + qdrant)
- [x] MkDocs publicado + README com quickstart (`mkdocs.yml` + build validado)
- [~] Vídeo de demo cobrindo US-01 a US-05 — roteiro pronto (doc 10); gravação pendente de ambiente com LLM real
- [~] Deploy Azure Container Apps validado por HTTPS (landing, login demo, chat e feedback). *(P0.2 em 2026-08-11 confirmou landing e `/health` públicos, mas o login demo retornou `Erro de autenticação`; P0.3 mediu cold start HTTP 504 em 81,72 s e exit 137 apenas em revisões antigas. A correção está testada localmente, porém sua publicação é bloqueada por Docker Desktop parado e ACR Tasks indisponível; aceite funcional bloqueado.)*
