# Evidencia do baseline RAG de 2026-08-06

## Escopo congelado

| Item | Valor |
|---|---|
| Relatorio | `src/evaluation/relatorio_ragas.md` |
| Gerado em | `2026-08-06T14:50:48.482095+00:00` |
| Modo | `Ragas+LLM` |
| Dataset | `src/evaluation/dataset.jsonl` |
| Dataset SHA-256 | `7cf2998f2f9f416a2e8a11f181fca7ca7dc743df7a6923c0380d8b439c966a20` |
| Relatorio SHA-256 | `cc83f65c018dd897bff2ee4cf7d9604d97cee120e0cb04c144d8f1dfc9efd180` |
| Manifest SHA-256 | `9ad6307e701d7a7fb252e86d8a69faa85e2ca2de611f29397b89e60f06742a43` |

O inventario versionado esta em
`src/evaluation/baseline_diagnostico_2026-08-06.json` (schema `1.0.0`).
Ele preserva as metricas historicas sem reexecutar Ragas, alterar corpus ou
alterar runtime.

## Comparacao do inventario com o relatorio historico

| Verificacao | Inventario | Relatorio | Resultado |
|---|---:|---:|---|
| IDs unicos q001-q030 | 30 | 30 | Confere |
| `tool` | 4 | 4 | Confere |
| `composta` | 3 | 3 | Confere |
| `fora_de_escopo` | 4 | 4 | Confere |
| `direct` | 14 | 15 | Divergencia historica em q022 |
| `sem_resposta` | 5 | 4 | Divergencia historica em q022 |
| Notas zero | 9 | 9 | Confere |

As 30 duplas de `faithfulness` e `answer_relevancy` do inventario reproduzem
a tabela "Detalhe por pergunta" do relatorio. A divergencia de categoria e
intencionalmente preservada, sem reescrever a evidencia historica: o
`dataset.jsonl` atual classifica q022 como `sem_resposta`, enquanto o relatorio
de 06/08/2026 a publicou como `direct`.

## Diagnostico de notas zero

| IDs | Causa versionada | Evidencia rastreavel |
|---|---|---|
| q009, q010, q024, q025 | `inadequacao_metrica` | "Leitura critica", item 1 do relatorio: o redirecionamento RF-10 esta correto, mas sem contexto recebe zero de faithfulness/relevancy. |
| q018, q019, q020, q021, q022 | `fonte_ausente` | "Leitura critica", item 2 do relatorio: q018-q022 zeraram porque o Guia do Servidor indexado nao contem as respostas; para q020, a Lei 8.112/90 tambem nao aparece no `manifest.json` congelado. |

Nenhuma causa de recuperacao inadequada ou resposta insuficiente foi atribuida:
o relatorio nao fornece evidencia para essas causas nos casos zero. O
diagnostico nao infere falha de pipeline quando a propria leitura critica
registra lacuna de corpus.

## Taxonomia congelada

| Categoria | Tratamento futuro definido pela decisao provisoria |
|---|---|
| `direct` | Pergunta documental recuperavel; uma linha por pergunta no baseline. |
| `tool` | Fora do agregado RAG; validar valor, autorizacao e ausencia de recuperacao deterministicamente. |
| `composta` | Preserva linha historica; futuro agregado considera apenas subperguntas recuperaveis e sempre publica sub-relatorio. |
| `fora_de_escopo` | Fora do agregado; medir redirecionamento correto ao escopo UsiEdu e zero chamada de RAG/agentes. |
| `sem_resposta` | Fora do agregado; medir recusa honesta e ausencia de fonte inventada. |

Essas regras classificam e protegem a leitura do baseline. Elas nao
implementam agregador, roteamento, subperguntas ou mudanca de comportamento;
esses itens permanecem exclusivos de T02.3 e das microtarefas posteriores.
