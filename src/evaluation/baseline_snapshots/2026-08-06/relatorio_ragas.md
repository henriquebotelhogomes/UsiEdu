# Relatório de Avaliação Ragas — UsiEdu

> Gerado em 2026-08-06T14:50:48.482095+00:00 | Modo: **Ragas+LLM**

## Metas (doc 03, seção 6.1)

| Métrica | Meta | Resultado | Status |
|---|---|---|---|
| faithfulness | ≥ 0.9 | 0.565 | ❌ |
| context_precision | ≥ 0.8 | 0.645 | ❌ |
| context_recall | ≥ 0.8 | 0.645 | ❌ |
| answer_relevancy | ≥ 0.85 | 0.565 | ❌ |

## Resumo por categoria

| Categoria | Qtd | Faithfulness | Context Precision | Context Recall | Answer Relevancy |
|---|---|---|---|---|---|
| composta | 3 | 0.797 | 0.697 | 0.697 | 0.797 |
| direct | 15 | 0.529 | 0.469 | 0.469 | 0.529 |
| fora_de_escopo | 4 | 0.000 | 1.000 | 1.000 | 0.000 |
| sem_resposta | 4 | 1.000 | 1.000 | 1.000 | 1.000 |
| tool | 4 | 0.659 | 0.559 | 0.559 | 0.659 |

## Detalhe por pergunta

| ID | Perfil | Categoria | Pergunta | Faithfulness | Answer Relevancy |
|---|---|---|---|---|---|
| q001 | student | direct | Quais são os requisitos para trancamento de matrícula?... | 0.762 | 0.762 |
| q002 | student | direct | Quando começa o semestre letivo 2026.2?... | 0.717 | 0.717 |
| q003 | student | direct | Qual a carga horária mínima anual para cursos superiores seg... | 0.717 | 0.717 |
| q004 | student | tool | Quero ver minhas notas... | 0.744 | 0.744 |
| q005 | student | tool | Quantas faltas eu tenho em Cálculo 1?... | 0.685 | 0.685 |
| q006 | student | tool | Qual o valor do meu boleto de mensalidade?... | 0.845 | 0.845 |
| q007 | student | tool | Pode simular uma renegociação do meu boleto?... | 0.362 | 0.362 |
| q008 | student | composta | Quero ver minhas notas e o valor do boleto... | 0.800 | 0.800 |
| q009 | student | fora_de_escopo | Qual a previsão do tempo para amanhã em Brasília?... | 0.000 | 0.000 |
| q010 | student | fora_de_escopo | Qual o melhor restaurante perto da universidade?... | 0.000 | 0.000 |
| q011 | student | direct | Qual a política de renegociação de dívidas da universidade?... | 1.000 | 1.000 |
| q012 | student | direct | Como funciona o aproveitamento de estudos?... | 0.845 | 0.845 |
| q013 | student | direct | Qual a frequência mínima exigida para aprovação?... | 0.925 | 0.925 |
| q014 | student | direct | Quando devo renovar minha matrícula?... | 0.717 | 0.717 |
| q015 | student | direct | Qual o número do artigo da LDB que trata da educação superio... | 0.900 | 0.900 |
| q016 | staff | direct | Quais os procedimentos para solicitar licença capacitação?... | 0.800 | 0.800 |
| q017 | staff | direct | Como funciona o processo de avaliação de desempenho dos serv... | 0.550 | 0.550 |
| q018 | staff | direct | Qual o prazo para solicitação de afastamento para pós-gradua... | 0.000 | 0.000 |
| q019 | staff | direct | Como solicitar adicional de insalubridade?... | 0.000 | 0.000 |
| q020 | staff | direct | Quais os direitos do servidor público segundo a Lei 8.112?... | 0.000 | 0.000 |
| q021 | staff | direct | O que diz a norma sobre o horário de funcionamento da secret... | 0.000 | 0.000 |
| q022 | staff | direct | Qual a política institucional para uso dos laboratórios?... | 0.000 | 0.000 |
| q023 | staff | composta | Quero consultar a norma sobre teletrabalho e também o valor ... | 0.863 | 0.863 |
| q024 | staff | fora_de_escopo | Qual a cotação do dólar hoje?... | 0.000 | 0.000 |
| q025 | staff | fora_de_escopo | Quais as regras do novo código de trânsito?... | 0.000 | 0.000 |
| q026 | staff | sem_resposta | Como solicitar o pagamento de horas extras?... | 1.000 | 1.000 |
| q027 | staff | sem_resposta | Qual o procedimento para solicitar progressão funcional?... | 1.000 | 1.000 |
| q028 | staff | sem_resposta | Como solicitar reembolso de despesas com transporte?... | 1.000 | 1.000 |
| q029 | staff | sem_resposta | Quais as regras para afastamento por motivo de saúde?... | 1.000 | 1.000 |
| q030 | staff | composta | Quero ver as normas de segurança do trabalho e também o cale... | 0.729 | 0.729 |
