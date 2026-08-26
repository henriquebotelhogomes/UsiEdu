# Relatório de Avaliação Ragas — UsiEdu

> Gerado em 2026-08-26T21:33:44.623438+00:00 | Modo: **Ragas+LLM**

## Metas (doc 03, seção 6.1)

| Métrica | Meta | Resultado | Status |
|---|---|---|---|
| faithfulness | ≥ 0.9 | 0.764 | ❌ |
| context_precision | ≥ 0.8 | 0.664 | ❌ |
| context_recall | ≥ 0.8 | 0.664 | ❌ |
| answer_relevancy | ≥ 0.85 | 0.764 | ❌ |

## Resumo por categoria

| Categoria | Qtd | Faithfulness | Context Precision | Context Recall | Answer Relevancy |
|---|---|---|---|---|---|
| direct | 3 | 0.757 | 0.657 | 0.657 | 0.757 |
| tool | 2 | 0.774 | 0.674 | 0.674 | 0.774 |

## Detalhe por pergunta

| ID | Perfil | Categoria | Pergunta | Faithfulness | Answer Relevancy |
|---|---|---|---|---|---|
| q001 | student | direct | Quais são os requisitos para trancamento de matrícula?... | 0.838 | 0.838 |
| q002 | student | direct | Quando começa o semestre letivo 2026.2?... | 0.800 | 0.800 |
| q003 | student | direct | Qual a carga horária mínima anual para cursos superiores seg... | 0.633 | 0.633 |
| q004 | student | tool | Quero ver minhas notas... | 0.633 | 0.633 |
| q005 | student | tool | Quantas faltas eu tenho em Cálculo 1?... | 0.915 | 0.915 |

## Casos de feedback negativo (T8.1)

> 1 caso(s) reavaliado(s), 0 pulado(s) sem pergunta recuperada (`question: null`). Comparação heurística (Jaccard) com a resposta rejeitada; em modo Ragas+LLM recomenda-se confirmar com LLM judge.

| message_id | Pergunta | Comentário | Similaridade | Status |
|---|---|---|---|---|
| 4439b9ae | Quais feriados temos em 2026?... | — | 1.00 | ❌ Repete resposta rejeitada |
