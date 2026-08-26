# PRD v3 — UsiEdu: Arquitetura Multi-Agente Enterprise (Padrão Startup Global / Série A+)

> **Documento de Especificação Técnica e Arquitetural v3.**
> Focado na maturidade enterprise dos padrões **LangChain** e **LangGraph**, estruturação estrita de saídas com Pydantic, chamada nativa de ferramentas (*function calling*), síntese cognitiva de respostas compostas e governança de contexto.

---

## 1. Objetivo da Versão v3

Elevar o ecossistema de orquestração multi-agente do UsiEdu ao mais alto padrão de engenharia de software para IA, eliminando fragilidades de parsing textual e tornando o fluxo de agentes totalmente determinístico, auditável e resiliente.

### Principais Pilares da v3:
1. **Roteamento Determinístico (Structured Outputs):** Substituição do parse manual de JSON string no Supervisor por `with_structured_output` com Pydantic Schema Enforcement.
2. **Function Calling Nativo (`@tool` & `bind_tools`):** Substituição de regex/keyword matching nos agentes por ferramentas nativas do LangChain invocadas dinamicamente pela LLM.
3. **Consolidação com Síntese Cognitiva:** Em perguntas compostas multitemáticas, as respostas parciais dos agentes são unificadas por um nó de síntese via LLM, garantindo coesão e estilo natural.
4. **Gerenciamento Inteligente de Contexto (`trim_messages`):** Poda automática de tokens na janela de contexto para evitar estouro de limites e vazamento de histórico entre turnos.
5. **Observabilidade e Resiliência de Streaming:** Garantia de continuidade do streaming SSE (`astream_events` v2) com rastreamento granular no LangSmith.

---

## 2. Requisitos Funcionais (RF3-xx)

### 2.1 Orquestração e Roteamento
- **RF3-01 (Supervisor Structured Output):** O nó Supervisor deve invocar o modelo utilizando `with_structured_output(SupervisorDecision)` ou fallback estruturado compatível, garantindo que o retorno seja sempre uma instância válida de `SupervisorDecision` com campos `intent`, `plan` e `reasoning`.
- **RF3-02 (Guardrail de Perfil):** O roteamento condicional deve validar que intenções restritas (ex.: `institucional`) só sejam despachadas para perfis autorizados (`staff`), mantendo conformidade com RBAC.

### 2.2 Agentes Especialistas e Ferramentas Nativas
- **RF3-03 (LangChain Native Tools):** Todas as funções de consulta de dados externos (ex.: `get_notas`, `get_faltas`, `consultar_extrato`, `gerar_boleto`) devem ser decoradas com `@tool` do LangChain com tipos de entrada e saídas estritos.
- **RF3-04 (Tool Binding):** Os modelos dos agentes (`academico`, `financeiro`) devem ser inicializados com `bind_tools(tools)` e processar chamadas de ferramenta através de execução assíncrona orientada pela LLM.

### 2.3 Síntese e Consolidação
- **RF3-05 (Single-Agent Fast Path):** Quando apenas um agente for acionado, a resposta deve seguir direto para saída sem custo adicional de tokens de síntese.
- **RF3-06 (Multi-Agent Cognitive Synthesis):** Quando múltiplos agentes responderem a uma pergunta composta, o nó de consolidação deve invocar uma cadeia de síntese para mesclar as respostas, remover redundâncias e gerar uma resposta final integrada.

### 2.4 Memória e Janela de Contexto
- **RF3-07 (Token Trimming):** Antes de injetar o histórico de mensagens no prompt de qualquer agente ou supervisor, o histórico deve ser podado utilizando `trim_messages` respeitando um teto máximo de tokens configurável.

---

## 3. Matriz de Componentes Afetados

| Componente | Arquivo | Natureza da Alteração |
|---|---|---|
| **Estado do Grafo** | `src/orchestration/state.py` | Schema `SupervisorDecision` com `Pydantic` e serialização JSON |
| **Supervisor** | `src/orchestration/supervisor.py` | `with_structured_output` + fallback robusto |
| **Ferramentas Acadêmicas** | `src/tools/academico_tools.py` | Decorators `@tool` e tipagem estrita |
| **Ferramentas Financeiras** | `src/tools/financeiro_tools.py` | Decorators `@tool` e tipagem estrita |
| **Agente Acadêmico** | `src/agents/academico.py` | Tool binding + execução nativa |
| **Agente Financeiro** | `src/agents/financeiro.py` | Tool binding + execução nativa |
| **Consolidação** | `src/orchestration/consolidation.py` | Síntese de perguntas compostas via LLM |
| **Utilitários de Chat** | `src/api/chat_common.py` | `trim_messages` para gestão de janela |

---

## 4. Checklist Executivo de Implementação e Status

| ID | Atividade / Requisito | Status | Arquivo Alvo | Evidência de Validação |
| :---: | :--- | :---: | :--- | :--- |
| **ACT-01** | Refatorar `SupervisorDecision` para schema estruturado com compatibilidade dict e properties | ✅ **Concluído** | `src/orchestration/state.py` | `test_supervisor.py`, `test_graph.py` |
| **ACT-02** | Implementar `with_structured_output` no nó Supervisor com fallback resiliente para JSON parsing | ✅ **Concluído** | `src/orchestration/supervisor.py` | `test_supervisor.py` (15/15 testes passando) |
| **ACT-03** | Decorar ferramentas acadêmicas (`get_notas`, `get_faltas`) com `@tool` do LangChain | ✅ **Concluído** | `src/tools/academico_tools.py` | `test_academico.py` (17/17 testes passando) |
| **ACT-04** | Decorar ferramentas financeiras (`get_boletos`, `simular_renegociacao`, `get_politica_renegociacao`) com `@tool` | ✅ **Concluído** | `src/tools/financeiro_tools.py` | `test_financeiro.py` (10/10 testes passando) |
| **ACT-05** | Integrar `bind_tools` aos nós especialistas acadêmico e financeiro | ✅ **Concluído** | `src/agents/academico.py`<br>`src/agents/financeiro.py` | `test_academico.py`, `test_financeiro.py` |
| **ACT-06** | Implementar nó de Consolidação com Síntese Cognitiva via LLM e Fast-Path para agente único | ✅ **Concluído** | `src/orchestration/consolidation.py`<br>`src/orchestration/graph.py` | `test_graph.py` (14/14 testes passando) |
| **ACT-07** | Adicionar poda de janela de contexto com `trim_messages` do LangChain | ✅ **Concluído** | `src/api/chat_common.py` | `test_api.py`, `test_chat_stream.py` |
| **ACT-08** | Ajustar Dockerfile e infraestrutura de persistência SQLite no Azure Files | ✅ **Concluído** | `Dockerfile.api`<br>`src/storage/database.py` | `test_deploy_config.py` (17/17 testes passando) |
| **ACT-09** | Execução e aprovação da suíte completa de testes unitários (314 testes) | ✅ **Concluído** | `tests/unit/` | `pytest tests/unit/` (314 passed, 0 failed) |
| **ACT-10** | Verificação estática de código com linter Ruff (0 erros) | ✅ **Concluído** | `src/`, `tests/` | `ruff check src/ tests/` (All checks passed!) |
