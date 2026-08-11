# Evidencia do baseline RAG de 2026-08-06

## Proveniencia congelada

| Item | Valor |
|---|---|
| Commit da execucao | `9f7c9bc73c1def78dd2efc489a022a6541d8ff74` |
| Dataset Git blob | `7d643a666021218443598288c5c8f5acc5b7ef81` |
| Manifest Git blob | `d49071f2c96a856f52cfc610adce7e02f9886d91` |
| Relatorio Git blob | `6e9bcfccbcdc1e455ce193cb8bd704e80d416840` |
| Snapshot dataset blob | `7d643a666021218443598288c5c8f5acc5b7ef81` |
| Snapshot manifest blob | `6eafd08a1d1c27f99a41441955b41f33500ebc2e` |
| Snapshot relatorio blob | `6e9bcfccbcdc1e455ce193cb8bd704e80d416840` |
| Gerado em | `2026-08-06T14:50:48.482095+00:00` |
| Modo declarado pelo relatorio | `Ragas+LLM` |

Os identificadores sao SHA-1 de objetos Git (`blob`): o Git calcula o hash
sobre `blob <tamanho>\0<bytes>`. Os tres primeiros sao referencias historicas
recuperadas do commit; os tres `Snapshot` sao calculados sobre os snapshots
versionados em `baseline_snapshots/2026-08-06/`, com bytes UTF-8 e LF
canonicos (o teste normaliza `CRLF` para `LF` antes do hash). O teste calcula
esses IDs em Python, sem `git show` ou `git rev-parse`, e por isso nao depende
de historico completo no CI.

O inventario em `baseline_diagnostico_2026-08-06.json` schema `2.0.0` usa os
snapshots para validacao local e conserva os IDs historicos como referencia de
origem. Ele nao associa os scores ao dataset ou manifest atuais.

## Modo declarado e mecanismo observado

O cabecalho do relatorio no commit historico declara `Ragas+LLM`. O
`src/evaluation/run_ragas.py` daquele mesmo commit, contudo, calcula scores
por `_avaliar_resposta`, descrita no codigo como heuristica, e nao importa nem
invoca a biblioteca Ragas. A chave de ambiente apenas seleciona o rotulo
`Ragas+LLM` e o grafo a executar; ela nao altera o calculo de scores.

O loop tambem converte qualquer `Exception` em quatro metricas `0.0`. O
relatorio nao preserva respostas produzidas, contextos, excecoes nem logs por
pergunta. Assim, o mecanismo observado e `heuristic_scoring`; o modelo, a
configuracao, os parametros do juiz e a ocorrencia de excecao por caso nao
foram registrados. Esta evidencia nao afirma que houve chamada Ragas real.

## Comparacao do inventario com os artefatos da execucao

| Verificacao | Dataset/relatorio do commit `9f7c9bc` | Inventario | Resultado |
|---|---:|---:|---|
| IDs unicos q001-q030 | 30 | 30 | Confere |
| `tool` | 4 | 4 | Confere |
| `composta` | 3 | 3 | Confere |
| `fora_de_escopo` | 4 | 4 | Confere |
| `direct` | 15 | 15 | Confere |
| `sem_resposta` | 4 | 4 | Confere |
| Pares faithfulness/relevancy | 30 | 30 | Confere |
| Notas zero | 9 | 9 | Confere |

## Revisao posterior de q022

O commit posterior `80d27c306bcf8c14eb732d13d48d09d0714db2e6` usa o dataset
blob `67933038582591b4009f9b2aba1286bf85a4ada3` e reclassifica q022 de
`direct` para `sem_resposta`, mudando tambem sua referencia e documentos.
Essa revisao e registrada separadamente no inventario. Ela nao altera o
snapshot nem a comparacao historica acima.

## Diagnostico de notas zero

| IDs | Diagnostico | Evidencia disponivel |
|---|---|---|
| q009, q010, q018-q022, q024, q025 | `indeterminada` | O relatorio registra apenas os scores. Respostas e erros brutos nao foram preservados, e o codigo poderia transformar excecao em quatro zeros. |

Nao e possivel provar para uma nota zero se a causa foi fonte ausente,
recuperacao inadequada, resposta insuficiente ou inadequacao de metrica. A
leitura critica adicionada posteriormente nao substitui os artefatos brutos da
execucao historica. Tambem nao se afirma recusa honesta nem ausencia de fonte
inventada sem resposta e fontes efetivamente registradas.

## Taxonomia congelada

| Categoria | Tratamento futuro definido pela decisao provisoria |
|---|---|
| `direct` | Pergunta documental recuperavel; uma linha por pergunta no baseline. |
| `tool` | Fora do agregado RAG; validar valor, autorizacao e ausencia de recuperacao deterministicamente. |
| `composta` | Preserva linha historica; futuro agregado considera apenas subperguntas recuperaveis e sempre publica sub-relatorio. |
| `fora_de_escopo` | Fora do agregado; medir redirecionamento correto ao escopo UsiEdu e zero chamada de RAG/agentes. |
| `sem_resposta` | Fora do agregado; medir recusa honesta e ausencia de fonte inventada. |

As regras sao requisitos para avaliacao futura, nao evidencia de que esses
comportamentos foram observados nesta execucao historica.

## Pendencia real de T02.1

T02.1 permanece parcial. A proveniencia de commit, dataset, manifest,
relatorio e mecanismo de score foi recuperada, mas o modelo,
configuracao/parametros do juiz e saidas/erros por caso nao sao recuperaveis a
partir dos artefatos versionados. Nenhum valor foi inferido.
