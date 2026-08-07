# UsiEdu — Documentação Técnica

**UsiEdu** é uma plataforma multi-agente de IA conversacional para educação,
desenvolvida como piloto para atendimento de dúvidas acadêmicas, financeiras e
institucionais com respostas fundamentadas em documentos oficiais.

## O que a plataforma faz

- Responde perguntas de **estudantes** (matrícula, notas, faltas, calendário, boletos)
  e de **servidores** (normas internas, direitos, políticas institucionais).
- Usa **RAG híbrido** (busca vetorial + BM25 + reranking) sobre documentos reais,
  sempre **citando a fonte** de cada resposta.
- Orquestra agentes especializados via **LangGraph** com supervisor de intenções,
  memória de sessão e tratamento educado de perguntas fora de escopo.

## Navegação recomendada

| Seção | Por onde começar |
|---|---|
| Arquitetura geral | [Visão Geral da Arquitetura](01-visao-geral-arquitetura.md) |
| Agentes e fluxo de conversa | [Agentes e Orquestração](02-agentes-e-orquestracao.md) |
| Pipeline RAG e infraestrutura | [RAG e Infraestrutura](03-rag-e-infraestrutura.md) |
| Escopo do piloto e critérios de aceite | [Piloto e Roadmap](04-piloto-e-roadmap.md) |
| Requisitos (PRD) | [PRD e Requisitos](07-prd-requisitos.md) |
| Contratos de API | [Contratos Técnicos](09-contratos-tecnicos.md) |

## Stack principal

- **Backend:** Python 3.12, FastAPI, LangGraph, LangChain
- **RAG:** Qdrant (2 coleções), sentence-transformers, BM25, reranker cross-encoder
- **Frontend:** React + Vite (TypeScript)
- **Qualidade:** pytest (cobertura ≥ 80%), Ruff, avaliação Ragas, MkDocs Material

## Repositório

O código-fonte e a documentação estão em
[github.com/henriquebotelhogomes/UsiEdu](https://github.com/henriquebotelhogomes/UsiEdu).
