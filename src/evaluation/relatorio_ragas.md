# Relatório de Avaliação Ragas — UsiEdu

> Gerado em 2026-09-01T13:35:50.836935+00:00 | Modo: **LLM-as-a-Judge (deepseek-v4-flash)**

## Metas (doc 03, seção 6.1)

| Métrica | Meta | Resultado | Status |
|---|---|---|---|
| faithfulness | ≥ 0.9 | 0.933 | ✅ |
| context_precision | ≥ 0.8 | 0.633 | ❌ |
| context_recall | ≥ 0.8 | 0.900 | ✅ |
| answer_relevancy | ≥ 0.85 | 0.933 | ✅ |

## Resumo por categoria

| Categoria | Qtd | Faithfulness | Context Precision | Context Recall | Answer Relevancy |
|---|---|---|---|---|---|
| direct | 3 | 0.933 | 0.633 | 0.900 | 0.933 |

## Detalhe por pergunta

| ID | Perfil | Categoria | Pergunta | Faithfulness | Answer Relevancy |
|---|---|---|---|---|---|
| q001 | student | direct | Quais são os requisitos para trancamento de matrícula?... | 1.000 | 1.000 |
| q002 | student | direct | Quando começa o semestre letivo 2026.2?... | 1.000 | 1.000 |
| q003 | student | direct | Qual a carga horária mínima anual para cursos superiores seg... | 0.800 | 0.800 |

## Casos de feedback negativo (T8.1)

> 1 caso(s) reavaliado(s), 0 pulado(s) sem pergunta recuperada (`question: null`). Comparação heurística (Jaccard) com a resposta rejeitada; em modo Ragas+LLM recomenda-se confirmar com LLM judge.

| message_id | Pergunta | Comentário | Similaridade | Status |
|---|---|---|---|---|
| 4439b9ae | Quais feriados temos em 2026?... | — | 0.04 | 🔄 Alterada — revisão manual |
