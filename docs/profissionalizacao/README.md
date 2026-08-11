# Programa de Profissionalização do UsiEdu

Este diretório transforma o arquivo raiz `PLANO_PROFISSIONALIZACAO.md` em
trabalho executável. Ele existe para que qualquer pessoa ou LLM consiga
continuar o projeto sem depender de contexto oral ou de inferências sobre o
estado do ambiente.

## Ordem de leitura para um implementador

1. Ler o [PRD do programa](00-prd-programa.md).
2. Ler o documento da iniciativa que será executada.
3. Conferir os checklists de progresso em `docs/08-plano-execucao.md`, os
   critérios de aceite em `docs/04-piloto-e-roadmap.md` e o gate de entrega em
   `docs/07-prd-requisitos.md`.
4. Ler os contratos ou decisões referenciados pela iniciativa.
5. Executar **uma microtarefa por vez**, registrando evidência e atualizando os
   checklists no mesmo commit.

## Documentos

| Documento | Estado | Propósito |
|---|---|---|
| [00 — PRD do programa](00-prd-programa.md) | Ativo | Governança, métricas e regras comuns a todas as iniciativas. |
| [01 — Validação do piloto](01-validacao-piloto.md) | Concluído | Validação do ambiente Azure público. |
| [02 — Qualidade RAG](02-qualidade-rag.md) | Especificado — não iniciado | Elevar métricas e cobertura do RAG. |
| [03 — Integração, entrega e rollback](03-integracao-entrega-rollback.md) | Especificado — não iniciado | Integração, CI/CD, tags imutáveis e rollback. |
| [04 — Segurança operacional](04-seguranca-operacional.md) | Especificado — não iniciado | Segredos, LGPD, backup e continuidade. |
| [05 — Performance e disponibilidade](05-performance-disponibilidade.md) | Especificado — não iniciado | Startup, escala, probes, timeout e resiliência. |
| [06 — Produto e experiência](06-produto-experiencia.md) | Especificado — não iniciado | Mensagens de erro, acessibilidade, mobile e portfólio. |
| [Template de iniciativa](TEMPLATE_INICIATIVA.md) | Ativo | Modelo obrigatório para as próximas iniciativas. |

## Convenções de estado

- `[ ]` — não iniciado;
- `[~]` — bloqueado, adiado ou parcialmente validado; incluir motivo e próximo
  passo;
- `[x]` — concluído, com evidência no próprio item ou em documento referenciado.

O status do trabalho é mantido nos checklists legados acima. Este diretório
explica o plano e armazena evidências complementares; ele não deve criar um
segundo status conflitante.
