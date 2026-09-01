# Relatório de Avaliação Ragas — UsiEdu

> Gerado em 2026-08-31T20:57:34.400446+00:00 | Modo: **heurística de cobertura + LLM (não é o framework Ragas)**

## Metas (doc 03, seção 6.1)

| Métrica | Meta | Resultado | Status |
|---|---|---|---|
| faithfulness | ≥ 0.9 | 0.767 | ❌ |
| context_precision | ≥ 0.8 | 0.733 | ❌ |
| context_recall | ≥ 0.8 | 0.733 | ❌ |
| answer_relevancy | ≥ 0.85 | 0.767 | ❌ |

## Resumo por categoria

| Categoria | Qtd | Faithfulness | Context Precision | Context Recall | Answer Relevancy |
|---|---|---|---|---|---|
| composta | 3 | 0.000 | 0.000 | 0.000 | 0.000 |
| direct | 14 | 0.300 | 0.200 | 0.200 | 0.300 |
| fora_de_escopo | 4 | 1.000 | 1.000 | 1.000 | 1.000 |
| sem_resposta | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| tool | 4 | 0.000 | 0.000 | 0.000 | 0.000 |

## Detalhe por pergunta

| ID | Perfil | Categoria | Pergunta | Faithfulness | Answer Relevancy |
|---|---|---|---|---|---|
| q001 | student | direct | Quais são os requisitos para trancamento de matrícula?... | — | — |
| q002 | student | direct | Quando começa o semestre letivo 2026.2?... | — | — |
| q003 | student | direct | Qual a carga horária mínima anual para cursos superiores seg... | — | — |
| q004 | student | tool | Quero ver minhas notas... | — | — |
| q005 | student | tool | Quantas faltas eu tenho em Cálculo 1?... | — | — |
| q006 | student | tool | Qual o valor do meu boleto de mensalidade?... | — | — |
| q007 | student | tool | Pode simular uma renegociação do meu boleto?... | — | — |
| q008 | student | composta | Quero ver minhas notas e o valor do boleto... | — | — |
| q009 | student | fora_de_escopo | Qual a previsão do tempo para amanhã em Brasília?... | 1.000 | 1.000 |
| q010 | student | fora_de_escopo | Qual o melhor restaurante perto da universidade?... | 1.000 | 1.000 |
| q011 | student | direct | Qual a política de renegociação de dívidas da universidade?... | — | — |
| q012 | student | direct | Como funciona o aproveitamento de estudos?... | — | — |
| q013 | student | direct | Qual a frequência mínima exigida para aprovação?... | — | — |
| q014 | student | direct | Quando devo renovar minha matrícula?... | — | — |
| q015 | student | direct | Qual o número do artigo da LDB que trata da educação superio... | 0.300 | 0.300 |
| q016 | staff | direct | Quais os procedimentos para solicitar licença capacitação?... | — | — |
| q017 | staff | direct | Como funciona o processo de avaliação de desempenho dos serv... | — | — |
| q018 | staff | direct | Qual o prazo para solicitação de afastamento para pós-gradua... | — | — |
| q019 | staff | direct | Como solicitar adicional de insalubridade?... | — | — |
| q020 | staff | direct | Quais os direitos do servidor público segundo a Lei 8.112?... | — | — |
| q021 | staff | direct | O que diz a norma sobre o horário de funcionamento da secret... | — | — |
| q022 | staff | sem_resposta | Qual a política institucional para uso dos laboratórios?... | — | — |
| q023 | staff | composta | Quero consultar a norma sobre teletrabalho e também o valor ... | — | — |
| q024 | staff | fora_de_escopo | Qual a cotação do dólar hoje?... | — | — |
| q025 | staff | fora_de_escopo | Quais as regras do novo código de trânsito?... | — | — |
| q026 | staff | sem_resposta | Como solicitar o pagamento de horas extras?... | — | — |
| q027 | staff | sem_resposta | Qual o procedimento para solicitar progressão funcional?... | — | — |
| q028 | staff | sem_resposta | Como solicitar reembolso de despesas com transporte?... | — | — |
| q029 | staff | sem_resposta | Quais as regras para afastamento por motivo de saúde?... | — | — |
| q030 | staff | composta | Quero ver as normas de segurança do trabalho e também o cale... | — | — |

## Casos de feedback negativo (T8.1)

> 1 caso(s) reavaliado(s), 0 pulado(s) sem pergunta recuperada (`question: null`). Comparação heurística (Jaccard) com a resposta rejeitada; em modo Ragas+LLM recomenda-se confirmar com LLM judge.

| message_id | Pergunta | Comentário | Similaridade | Status |
|---|---|---|---|---|
| 4439b9ae | Quais feriados temos em 2026?... | — | — | 💥 Falha ao reexecutar |
