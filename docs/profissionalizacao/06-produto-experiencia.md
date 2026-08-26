# P2 — Produto e experiência

| Campo | Valor |
|---|---|
| Estado | Planejado — especificado, não iniciado |
| Prioridade | P2 |
| Dono | Henrique Botelho Gomes |
| Dependências | [PRD do programa](00-prd-programa.md), `frontend/src/`, `PRD.v2.md`, `scripts/capture_screenshots.py` |
| Documentos normativos | `PLANO_PROFISSIONALIZACAO.md`; `PRD.v2.md` RF2-01–05 e RNF2-06; `docs/04-piloto-e-roadmap.md` §§ 5 e 8; `docs/07-prd-requisitos.md` RF-24–27 e RNF-05; `docs/08-plano-execucao.md` T7.1–T7.4; `docs/09-contratos-tecnicos.md` § 2 |
| Checklists legados afetados | `docs/04-piloto-e-roadmap.md` § 5 e § 8; `docs/07-prd-requisitos.md` § 7; `docs/08-plano-execucao.md` T7.1–T7.4. Não alterar status nesta especificação. |
| Atualizado em | 2026-08-11 |

## 1. Contexto e evidências

O chat já usa SSE por `fetch`/`ReadableStream`, mostra cursor durante streaming
e preserva `/chat` como fallback. O PRD v2 registra que o fallback automático
ocorre em erro de rede/parse antes de receber tokens; se já houver tokens, o
cliente mantém conteúdo parcial para evitar duplicação. A P0 aprovou landing,
login, chat RAG, feedback e `/insights` em HTTPS.

RNF2-06 exige `aria-label` para botões/links novos e manutenção de navegação
por teclado. Links de fonte já recebem `aria-label`; a página `/insights`
existe e não há screenshot dela no conjunto documentado no README. O roteiro
de vídeo existe, enquanto o checklist legado ainda registra gravação pendente.
Antes deste pacote, não havia política para perguntas genéricas, padrão de
acessibilidade ou breakpoints; a decisão provisória agora os define. Destino de
contato, hospedagem/roteiro final do vídeo e licença continuam sem fato aprovado.

## 2. Objetivo mensurável

Garantir que falhas/interrupções do stream sejam compreensíveis e recuperáveis,
evidenciar navegação por teclado e uso em viewport mobile, e completar os
ativos públicos previstos (contato, vídeo e screenshot de `/insights`) após as
decisões correspondentes. Os fluxos principais usam como referência WCAG 2.2
AA nos viewports 360, 768 e 1280 px; contato, host/roteiro final do vídeo e
licença permanecem pendências factuais de publicação.

## 3. Escopo e não escopo

### Escopo

- Mensagem, estado e recuperação no chat quando stream falhar/interromper.
- Política explícita para pergunta genérica: conhecimento geral seguro,
ferramenta determinística ou redirecionamento.
- Revisão de acessibilidade, teclado e responsividade mobile.
- Página/canal de contato, vídeo curto e screenshot de `/insights`.

### Não escopo

- Novo agente, ferramenta externa, conteúdo institucional ou mudança de RAG.
- Aplicativo mobile nativo, redesenho integral ou autenticação nova.
- Prometer resposta genérica sem decisão de segurança/produto.

## 4. Requisitos e critérios de aceite

| ID | Requisito | Critério de aceite verificável |
|---|---|---|
| RQ-UX-01 | Falha antes/durante stream deve ter mensagem compreensível e ação segura. | Dado erro simulado, quando o usuário estiver no chat, então entende se a resposta não foi enviada, foi parcial ou pode ser repetida sem duplicação. |
| RQ-UX-02 | Pergunta genérica segura fora do domínio é redirecionada para o escopo UsiEdu sem RAG/agentes; operação determinística aprovada usa `tool`. | Casos de fronteira não oferecem conhecimento geral irrestrito e comprovam zero chamada indevida de RAG/agentes. |
| RQ-UX-03 | Elementos afetados devem funcionar por teclado e ter nome acessível, com WCAG 2.2 AA como referência dos fluxos principais. | Teste manual/automatizado percorre login, chat, fontes, feedback e insights sem foco perdido e verifica teclado, foco, nome acessível e contraste. |
| RQ-UX-04 | Fluxos principais devem permanecer utilizáveis em 360, 768 e 1280 px. | Evidência demonstra landing, login, chat e insights sem bloqueio funcional nos três viewports. |
| RQ-UX-05 | Ativos públicos devem ser verificáveis e atuais. | Conteúdo local pode ser preparado, mas contato, vídeo e mídia só são publicados após destino/host/roteiro/licença aprovados; não expõem dado/segredo. |

## 5. Decisões, dependências e riscos

| Tipo | Item | Dono / condição | Mitigação ou próximo passo |
|---|---|---|---|
| Decisão tomada | SSE conserva fallback `/chat` antes de tokens e evita duplicação após token parcial. | `PRD.v2.md` T7.3 e plano T7.3. | Preservar esse contrato ao melhorar mensagens. |
| Decisão tomada | RF-10 redireciona fora de escopo sem chamar agentes. | `docs/07` RF-10. | Não confundir pergunta genérica com categoria fora de escopo sem política. |
| Decisão provisória | Pergunta genérica segura fora do domínio é redirecionada ao escopo UsiEdu sem RAG/agentes; operações determinísticas aprovadas usam `tool`; não há conhecimento geral irrestrito. | Revisar com requisito de produto aprovado e casos de fronteira testados. | T06.2 pode especificar/testar casos; mudança de comportamento continua trabalho P2. |
| Decisão provisória | Viewports são 360, 768 e 1280 px; WCAG 2.2 AA referencia os fluxos principais, com teclado, foco, nome acessível e contraste. | Revisar se personas/dispositivos ou norma aplicável mudarem. | T06.3 pode auditar e registrar evidência sem alegar certificação. |
| Gate explícito de publicação | Screenshot de `/insights` pode ser publicado após revisão de conteúdo em sessão segura. Contato exige destino aprovado; vídeo exige host, roteiro final e licença aprovados. | Exige o fato aplicável a cada ativo, aprovado pelo proprietário/responsável. | T06.4 pode preparar conteúdo local; não precisa reter screenshot revisado por pendências de contato/vídeo. |
| Risco | Mensagem de retry pode duplicar pergunta/feedback ou ocultar resposta parcial. | Stream pode falhar após tokens. | Testar estados antes/depois do primeiro token. |
| Risco | Screenshot/vídeo pode vazar conta demo, token, URL interna ou dado operacional. | Ativo público. | Capturar em sessão limpa e revisar antes de versionar/publicar. |

## 6. Plano técnico

A futura implementação deve modelar explicitamente os estados do envio:
pendente, streaming sem token, parcial, final, falha recuperável e falha que
exige nova conversa. A interface não pode afirmar que uma resposta parcial foi
concluída nem reenviar automaticamente depois de tokens. Testes de parser SSE e
componentes existentes são o ponto de partida.

A política de pergunta genérica redireciona perguntas seguras fora do domínio
ao escopo UsiEdu, sem RAG/agentes; uma operação determinística aprovada usa
`tool`, e conhecimento geral irrestrito não é oferecido. A revisão de
acessibilidade inicia nos fluxos login/chat/feedback/fontes/insights, usando
WCAG 2.2 AA como referência e registrando browser, teclado, foco, nome
acessível, contraste e os viewports 360/768/1280 px. Ativos de portfólio podem
ser preparados localmente. Screenshot de `/insights` pode ser publicado após
revisão de conteúdo seguro; contato exige destino aprovado e vídeo/mídia exigem
host, roteiro final e licença aprovados.

## 7. Tarefas e microtarefas

- [ ] **T06.1 — Especificar estados de falha do stream**
  - [ ] Mapear mensagens, ações e persistência para falha antes/depois do primeiro token.
  - [ ] Teste: parser/API fake produz cada estado sem duplicar mensagem.
  - [ ] Evidência: matriz de estados e capturas de teste.
  - [ ] Commit esperado: `docs(ux): definir falhas de streaming`.
- [ ] **T06.2 — Decidir perguntas genéricas**
  - [ ] Registrar exemplos de redirecionamento sem RAG/agentes e de `tool` determinística aprovada; não oferecer conhecimento geral irrestrito.
  - [ ] Teste: casos de fronteira seguem a decisão e preservam RF-10/RF-14.
  - [ ] Evidência: decisão e testes de comportamento.
  - [ ] Commit esperado: `docs(produto): definir perguntas genericas`.
- [ ] **T06.3 — Revisar acessibilidade e mobile**
  - [ ] Auditar 360, 768 e 1280 px contra WCAG 2.2 AA como referência, incluindo teclado, foco, nome acessível e contraste.
  - [ ] Teste: componentes afetados exercitam teclado/`aria-label`; roteiro manual cobre mobile.
  - [ ] Evidência: checklist com browser, viewport, achados e correções.
  - [ ] Commit esperado: `test(ux): cobrir acessibilidade e mobile`.
- [ ] **T06.4 — Preparar ativos públicos**
  - [ ] Preparar conteúdo local e capturar `/insights` em sessão segura; publicar contato, vídeo ou mídia apenas após aprovação de contato, host/roteiro e licença.
  - [ ] Teste: links/rotas e imagens carregam sem conteúdo sensível.
  - [ ] Evidência: URLs, arquivo revisado e checklist de publicação.
  - [ ] Commit esperado: `docs(portfolio): atualizar ativos publicos`.

## 8. Estratégia de testes e validação

| Camada | Cenário | Automação | Comando / evidência |
|---|---|---|---|
| Unitária | Estados de stream, ações de retry e nomes acessíveis. | Sim | Vitest/Testing Library existentes. |
| Integração | SSE parcial/erro e fallback `/chat`. | Sim | API fake/proxy conforme contratos vigentes. |
| Manual | Teclado, leitor de tela quando definido, viewport mobile e ativos públicos. | Sim/Não | Checklist com browser, viewport e passos. |
| Azure | Fluxo P0 e screenshot/vídeo autorizados. | Manual | URL pública, sessão limpa e revisão de conteúdo. |

## 9. Encerramento

### Gates e reversibilidade

| Gate | Estado documental atual | Condição / evidência futura |
|---|---|---|
| G0 — Baseline | Concluído | PRD v2, P0 e UI existente inventariados. |
| G1 — Especificação | Concluído | Este documento define política de perguntas, viewports e referência; fatos de publicação bloqueiam somente a publicação dos ativos. |
| G2 — Implementação | Não iniciado | Commits T06.1–T06.4. |
| G3 — Verificação | Não iniciado | Testes de stream, acessibilidade e evidência manual. |
| G4 — Operação | Não iniciado | Fluxo público e ativos verificados sem dado sensível. |
| G5 — Encerramento | Não iniciado | Checklists legados reconciliados com evidência. |

Mensagens/estados de UI são reversíveis por commit e devem preservar o
fallback vigente. Ativos públicos devem ser removíveis por commit/host sem
alterar dados do produto. Política de perguntas genéricas não deve ser
publicada como comportamento até ser aprovada e testada.

### Definition of Done

- [ ] Falhas de stream têm comportamento testado e explicação clara.
- [ ] Política de pergunta genérica, WCAG 2.2 AA como referência e viewports estão decididos; publicação de ativos respeita o gate factual.
- [ ] Auditoria de teclado/mobile e ativos públicos têm evidência revisada.
- [ ] Fluxo P0 continua válido após mudanças de UX.
- [ ] Checklists legados só foram atualizados com a implementação validada.
