# Diretrizes de Desenvolvimento UsiEdu (.project/guidelines.md)

## 1. Regras de Código e Estilo
- **Python 3.12+**: Tipagem estrita com `from __future__ import annotations`, Pydantic v2 e TypedDicts para estados do LangGraph.
- **Linter e Formatador**: Ruff (`ruff check src/ tests/ scripts/`). Nenhuma alteração pode introduzir warnings ou erros de lint.
- **Testes Unitários**: 100% de passagem via `pytest tests/unit/`. Todas as novas rotas e nós do grafo devem conter testes unitários correspondentes.
- **RAGAS Gate**: Relatórios de avaliação de RAG não podem ficar abaixo do score de 0.80.

## 2. Padrões LangGraph & Multi-Agent
- **Zero Raw String Parsing**: Sempre utilize `with_structured_output` com schemas tipados para decisões de roteamento.
- **Tool Calling**: Declare tools com `@tool` e faça o bind via `bind_tools`.
- **Token Efficiency**: Sempre pode históricos com `trim_messages` e preserve o fast-path de agente único no nó de consolidação.
