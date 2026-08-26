# Relatório de Avaliação Ragas — UsiEdu

> Gerado em 2026-08-26T18:35:03.355527+00:00 | Modo: **Ragas+LLM**

## Metas (doc 03, seção 6.1)

| Métrica | Meta | Resultado | Status |
|---|---|---|---|
| faithfulness | ≥ 0.9 | 0.662 | ❌ |
| context_precision | ≥ 0.8 | 0.562 | ❌ |
| context_recall | ≥ 0.8 | 0.562 | ❌ |
| answer_relevancy | ≥ 0.85 | 0.662 | ❌ |

## Resumo por categoria

| Categoria | Qtd | Faithfulness | Context Precision | Context Recall | Answer Relevancy |
|---|---|---|---|---|---|
| direct | 2 | 0.662 | 0.562 | 0.562 | 0.662 |

## Detalhe por pergunta

| ID | Perfil | Categoria | Pergunta | Faithfulness | Answer Relevancy |
|---|---|---|---|---|---|
| q001 | student | direct | Quais são os requisitos para trancamento de matrícula?... | 0.608 | 0.608 |
| q002 | student | direct | Quando começa o semestre letivo 2026.2?... | 0.717 | 0.717 |

## Casos de feedback negativo (T8.1)

> 1 caso(s) reavaliado(s), 0 pulado(s) sem pergunta recuperada (`question: null`). Comparação heurística (Jaccard) com a resposta rejeitada; em modo Ragas+LLM recomenda-se confirmar com LLM judge.

| message_id | Pergunta | Comentário | Similaridade | Status |
|---|---|---|---|---|
| 4439b9ae | Quais feriados temos em 2026?... | — | 1.00 | ❌ Repete resposta rejeitada |
