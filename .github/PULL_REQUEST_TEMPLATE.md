## 📌 Descrição da Mudança
<!-- Descreva de forma clara e objetiva o que esta alteração faz e qual problema ela resolve. -->

## 🧩 Tipo de Alteração
- [ ] 🚀 Nova funcionalidade (`feat`)
- [ ] 🐛 Correção de bug (`fix`)
- [ ] ♻️ Refatoração arquitetural (`refactor`)
- [ ] ⚡ Melhoria de performance ou FinOps (`perf`)
- [ ] 📝 Atualização de documentação (`docs`)
- [ ] 🧪 Testes adicionais (`test`)
- [ ] 🔧 Ajuste de infraestrutura ou CI/CD (`ci` / `infra`)

## 🤖 Impacto nos Agentes e RAG
- [ ] Modifica o grafo de orquestração (`StateGraph` / nós de decisão)
- [ ] Altera a base vetorial ou a pipeline de busca híbrida (Qdrant / BM25 / Reranker)
- [ ] Afeta o consumo de tokens / prompts (necessita validação de `trim_messages`)
- [ ] Nenhuma alteração em agentes ou RAG

## ✅ Checklist de Qualidade Obrigatório
- [ ] Executei `ruff check .` e `ruff format --check .` sem erros.
- [ ] Executei `pytest tests/unit/` e todos os testes passaram.
- [ ] Assegurei que dados sensíveis/PII passam por `mask_pii`.
- [ ] O Semantic Cache foi considerado caso seja uma consulta pública/geral.
- [ ] Atualizei a documentação e os testes associados (se aplicável).
