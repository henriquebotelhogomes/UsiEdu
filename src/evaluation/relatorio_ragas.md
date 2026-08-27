# Relatório de Avaliação Ragas — UsiEdu

> Gerado em 2026-08-27T12:27:45.312985+00:00 | Modo: **Ragas+LLM**

## Metas (doc 03, seção 6.1)

| Métrica | Meta | Resultado | Status |
|---|---|---|---|
| faithfulness | ≥ 0.9 | 0.631 | ❌ |
| context_precision | ≥ 0.8 | 0.694 | ❌ |
| context_recall | ≥ 0.8 | 0.694 | ❌ |
| answer_relevancy | ≥ 0.85 | 0.631 | ❌ |

## Resumo por categoria

| Categoria | Qtd | Faithfulness | Context Precision | Context Recall | Answer Relevancy |
|---|---|---|---|---|---|
| composta | 3 | 0.722 | 0.622 | 0.622 | 0.722 |
| direct | 14 | 0.627 | 0.527 | 0.527 | 0.627 |
| fora_de_escopo | 4 | 0.000 | 1.000 | 1.000 | 0.000 |
| sem_resposta | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| tool | 4 | 0.742 | 0.642 | 0.642 | 0.742 |

## Detalhe por pergunta

| ID | Perfil | Categoria | Pergunta | Faithfulness | Answer Relevancy |
|---|---|---|---|---|---|
| q001 | student | direct | Quais são os requisitos para trancamento de matrícula?... | 0.838 | 0.838 |
| q002 | student | direct | Quando começa o semestre letivo 2026.2?... | 0.717 | 0.717 |
| q003 | student | direct | Qual a carga horária mínima anual para cursos superiores seg... | 0.300 | 0.300 |
| q004 | student | tool | Quero ver minhas notas... | 0.744 | 0.744 |
| q005 | student | tool | Quantas faltas eu tenho em Cálculo 1?... | 0.454 | 0.454 |
| q006 | student | tool | Qual o valor do meu boleto de mensalidade?... | 0.845 | 0.845 |
| q007 | student | tool | Pode simular uma renegociação do meu boleto?... | 0.925 | 0.925 |
| q008 | student | composta | Quero ver minhas notas e o valor do boleto... | 0.700 | 0.700 |
| q009 | student | fora_de_escopo | Qual a previsão do tempo para amanhã em Brasília?... | 0.000 | 0.000 |
| q010 | student | fora_de_escopo | Qual o melhor restaurante perto da universidade?... | 0.000 | 0.000 |
| q011 | student | direct | Qual a política de renegociação de dívidas da universidade?... | 0.300 | 0.300 |
| q012 | student | direct | Como funciona o aproveitamento de estudos?... | 0.573 | 0.573 |
| q013 | student | direct | Qual a frequência mínima exigida para aprovação?... | 0.925 | 0.925 |
| q014 | student | direct | Quando devo renovar minha matrícula?... | 0.633 | 0.633 |
| q015 | student | direct | Qual o número do artigo da LDB que trata da educação superio... | 0.900 | 0.900 |
| q016 | staff | direct | Quais os procedimentos para solicitar licença capacitação?... | 0.800 | 0.800 |
| q017 | staff | direct | Como funciona o processo de avaliação de desempenho dos serv... | 0.675 | 0.675 |
| q018 | staff | direct | Qual o prazo para solicitação de afastamento para pós-gradua... | 0.425 | 0.425 |
| q019 | staff | direct | Como solicitar adicional de insalubridade?... | 0.675 | 0.675 |
| q020 | staff | direct | Quais os direitos do servidor público segundo a Lei 8.112?... | 0.500 | 0.500 |
| q021 | staff | direct | O que diz a norma sobre o horário de funcionamento da secret... | 0.522 | 0.522 |
| q022 | staff | sem_resposta | Qual a política institucional para uso dos laboratórios?... | 1.000 | 1.000 |
| q023 | staff | composta | Quero consultar a norma sobre teletrabalho e também o valor ... | 0.738 | 0.738 |
| q024 | staff | fora_de_escopo | Qual a cotação do dólar hoje?... | 0.000 | 0.000 |
| q025 | staff | fora_de_escopo | Quais as regras do novo código de trânsito?... | 0.000 | 0.000 |
| q026 | staff | sem_resposta | Como solicitar o pagamento de horas extras?... | 1.000 | 1.000 |
| q027 | staff | sem_resposta | Qual o procedimento para solicitar progressão funcional?... | 1.000 | 1.000 |
| q028 | staff | sem_resposta | Como solicitar reembolso de despesas com transporte?... | 1.000 | 1.000 |
| q029 | staff | sem_resposta | Quais as regras para afastamento por motivo de saúde?... | 1.000 | 1.000 |
| q030 | staff | composta | Quero ver as normas de segurança do trabalho e também o cale... | 0.729 | 0.729 |

## Casos de feedback negativo (T8.1)

> 1 caso(s) reavaliado(s), 0 pulado(s) sem pergunta recuperada (`question: null`). Comparação heurística (Jaccard) com a resposta rejeitada; em modo Ragas+LLM recomenda-se confirmar com LLM judge.

| message_id | Pergunta | Comentário | Similaridade | Status |
|---|---|---|---|---|
| 4439b9ae | Quais feriados temos em 2026?... | — | 1.00 | ❌ Repete resposta rejeitada |
