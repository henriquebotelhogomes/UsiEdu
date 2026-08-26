# Comparação de juízes de avaliação — T02.5

- Comparação: `judge-comparison-2026-08-11`
- Subperguntas RAG: 17
- Registros: 102
- Custo estimado: US$ 0.319520 (teto US$ 5.00)

| Métrica | DeepSeek V4 Flash | Kimi K2.7 Code | Divergência absoluta |
|---|---:|---:|---:|
| faithfulness | 0.441176 | 0.650980 | 0.209804 |
| context_precision | 0.058824 | 0.062745 | 0.003922 |
| context_recall | 0.176471 | 0.166667 | 0.009804 |
| answer_relevancy | 0.423529 | 0.567647 | 0.144118 |

## Decisão

Manter provisoriamente o DeepSeek V4 Flash como juiz econômico. O Kimi K2.7 Code atribuiu scores maiores em faithfulness e answer relevancy, mas custou mais e apresentou maior amplitude nessas métricas. Sem calibração humana, scores maiores não demonstram maior correção; portanto, a evidência não justifica a troca.
