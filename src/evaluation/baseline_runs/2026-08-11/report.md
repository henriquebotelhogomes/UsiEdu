# Baseline auditável RAG — 2026-08-11

- Run ID: `baseline-2026-08-11`
- Commit da implementação/configuração: `f90907e619ca62c12d07308910449bc6ffd39e66`
- Dataset Git blob: `67933038582591b4009f9b2aba1286bf85a4ada3`
- Manifest Git blob: `1f16ac3fb74603b3a96a510024a35ae64aa63306`
- Modelos: router `deepseek-v4-flash`; agentes `deepseek-v4-pro`; temperatura `1.0`; máximo de saída `2048` tokens
- Mecanismo de score: `legacy_keyword_heuristic`
- Custo equivalente estimado: **US$ 0.030807** (teto: US$ 5.00)

> Este baseline preserva respostas, fontes, erros, duração e uso por caso. O mecanismo de score é a heurística legada e não executa métricas Ragas. Os valores abaixo não devem ser rotulados como avaliação Ragas real.

## Resultado agregado legado

| Métrica | Score |
|---|---:|
| faithfulness | 0.686705 |
| context_precision | 0.750947 |
| context_recall | 0.750947 |
| answer_relevancy | 0.686705 |

O agregado acima inclui todas as categorias apenas para comparação com o mecanismo legado. Ele não representa o futuro recorte RAG respondível.

## Comparação descritiva com 06/08/2026

| Métrica | Histórico | Novo auditável | Diferença |
|---|---:|---:|---:|
| faithfulness | 0.565000 | 0.686705 | +0.121705 |
| context_precision | 0.645000 | 0.750947 | +0.105947 |
| context_recall | 0.645000 | 0.750947 | +0.105947 |
| answer_relevancy | 0.565000 | 0.686705 | +0.121705 |

A comparação é somente descritiva: o histórico não preservou saídas brutas e usou o dataset anterior à reclassificação de q022. A diferença não demonstra melhora ou regressão causal.

## Sub-relatório por categoria

| Categoria | Casos | Sucessos | Fontes | Faithfulness | Context precision | Context recall | Answer relevancy |
|---|---:|---:|---:|---:|---:|---:|---:|
| composta | 3 | 3 | 10 | 0.797024 | 0.697024 | 0.697024 | 0.797024 |
| direct | 14 | 14 | 40 | 0.784633 | 0.686581 | 0.686581 | 0.784633 |
| fora_de_escopo | 4 | 4 | 0 | 0.000000 | 1.000000 | 1.000000 | 0.000000 |
| sem_resposta | 5 | 5 | 0 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| tool | 4 | 4 | 20 | 0.556301 | 0.456301 | 0.456301 | 0.556301 |

## Casos

| ID | Categoria | Status | Fontes | Duração (ms) | Tokens | Custo estimado (US$) | Faithfulness | Answer relevancy |
|---|---|---|---:|---:|---:|---:|---:|---:|
| q001 | direct | success | 5 | 27271 | 2138 | 0.00079569 | 0.684615 | 0.684615 |
| q002 | direct | success | 5 | 15098 | 4778 | 0.00217194 | 0.883333 | 0.883333 |
| q003 | direct | success | 5 | 16999 | 4239 | 0.00162669 | 0.883333 | 0.883333 |
| q004 | tool | success | 5 | 10911 | 3438 | 0.00135633 | 0.633333 | 0.633333 |
| q005 | tool | success | 5 | 16677 | 3893 | 0.00184623 | 0.838462 | 0.838462 |
| q006 | tool | success | 5 | 11034 | 2993 | 0.00125480 | 0.390909 | 0.390909 |
| q007 | tool | success | 5 | 8380 | 3662 | 0.00141672 | 0.362500 | 0.362500 |
| q008 | composta | success | 5 | 15372 | 7486 | 0.00365264 | 0.800000 | 0.800000 |
| q009 | fora_de_escopo | success | 0 | 2825 | 738 | 0.00005796 | 0.000000 | 0.000000 |
| q010 | fora_de_escopo | success | 0 | 3197 | 773 | 0.00006342 | 0.000000 | 0.000000 |
| q011 | direct | success | 5 | 14708 | 2685 | 0.00120309 | 1.000000 | 1.000000 |
| q012 | direct | success | 5 | 15779 | 2124 | 0.00089819 | 0.936364 | 0.936364 |
| q013 | direct | success | 5 | 13666 | 3159 | 0.00139773 | 0.925000 | 0.925000 |
| q014 | direct | success | 5 | 11775 | 4050 | 0.00170176 | 0.800000 | 0.800000 |
| q015 | direct | success | 5 | 19056 | 3329 | 0.00118984 | 0.900000 | 0.900000 |
| q016 | direct | success | 0 | 7837 | 1388 | 0.00042459 | 0.600000 | 0.600000 |
| q017 | direct | success | 0 | 7224 | 1414 | 0.00041221 | 0.675000 | 0.675000 |
| q018 | direct | success | 0 | 12482 | 1703 | 0.00045054 | 0.675000 | 0.675000 |
| q019 | direct | success | 0 | 10793 | 1581 | 0.00040924 | 0.800000 | 0.800000 |
| q020 | direct | success | 0 | 9609 | 1532 | 0.00050977 | 0.700000 | 0.700000 |
| q021 | direct | success | 0 | 9346 | 1406 | 0.00039577 | 0.522222 | 0.522222 |
| q022 | sem_resposta | success | 0 | 9438 | 1570 | 0.00054569 | 1.000000 | 1.000000 |
| q023 | composta | success | 5 | 15325 | 8983 | 0.00428808 | 0.862500 | 0.862500 |
| q024 | fora_de_escopo | success | 0 | 2008 | 741 | 0.00005908 | 0.000000 | 0.000000 |
| q025 | fora_de_escopo | success | 0 | 2542 | 785 | 0.00006454 | 0.000000 | 0.000000 |
| q026 | sem_resposta | success | 0 | 18182 | 1923 | 0.00067684 | 1.000000 | 1.000000 |
| q027 | sem_resposta | success | 0 | 12782 | 2054 | 0.00055213 | 1.000000 | 1.000000 |
| q028 | sem_resposta | success | 0 | 8271 | 1561 | 0.00044664 | 1.000000 | 1.000000 |
| q029 | sem_resposta | success | 0 | 8322 | 1438 | 0.00042796 | 1.000000 | 1.000000 |
| q030 | composta | success | 0 | 11671 | 1949 | 0.00051103 | 0.728571 | 0.728571 |

## Diagnóstico dos scores zero

| ID | Métricas | Causa | Evidência |
|---|---|---|---|
| q009 | faithfulness, answer_relevancy | inadequacao_de_metrica | resposta contém `fora do meu escopo`; fontes=0; delegações=1 |
| q010 | faithfulness, answer_relevancy | inadequacao_de_metrica | resposta contém `fora do meu escopo`; fontes=0; delegações=1 |
| q024 | faithfulness, answer_relevancy | inadequacao_de_metrica | resposta contém `fora do meu escopo`; fontes=0; delegações=1 |
| q025 | faithfulness, answer_relevancy | inadequacao_de_metrica | resposta contém `fora do meu escopo`; fontes=0; delegações=1 |

## Evidência bruta e limitações

- `records.jsonl` contém a pergunta, resposta integral, fontes/contextos, delegações, erro, duração, tokens, custo estimado e scores por caso.
- `provenance.json` contém hashes recalculáveis, commit, agregados e totais.
- O custo é uma estimativa equivalente por tokens baseada na tabela versionada em `config.json`; não é uma fatura emitida pelo provedor.
- Uma lista vazia de fontes demonstra apenas que nenhuma fonte chegou ao estado final do grafo; não identifica, sozinha, a causa da ausência.
- As decisões de recorte para categorias especiais continuam fora desta microtarefa e não são inferidas a partir do score heurístico.
