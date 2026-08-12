# Decisões provisórias do piloto

| Campo | Valor |
|---|---|
| Estado | Ativo — decisões provisórias; contrato de avaliação T02.3 implementado, sem mudança de runtime |
| Escopo | Iniciativas 02–06 do programa |
| Atualizado em | 2026-08-11 |
| Regra | Esta decisão destrava especificação, protocolo e testes locais; não conclui P1/P2 nem autoriza código, infraestrutura ou workflow. |

## Como usar

Este documento substitui bloqueios de decisão já resolvidos por decisões
conservadoras e revisáveis. Um **gate explícito** preserva um bloqueio factual:
ele informa a microtarefa que pode avançar e seu ponto obrigatório de parada.
Não é permitido preencher uma lacuna com credencial, acesso Azure, fonte
autorizada, fato jurídico ou medição inexistente.

## Registro transversal

| Área | Decisão provisória e racional | Revisão / validade | Iniciativa e efeito |
|---|---|---|---|
| RAG — recorte | `tool` fica fora do agregado RAG respondível: sua saída é determinística e deve validar valor, autorização e ausência de recuperação indevida. `composta` entra somente pelas subperguntas recuperáveis e recebe sub-relatório por subpergunta. O contrato versionado registra `id`, `categoria`, `requires_retrieval` e expectativa; o agregado é a média simples dessas subperguntas. Isso evita atribuir qualidade RAG a operação determinística sem esconder a parte recuperada. | Rever se taxonomia, roteamento ou dataset versionado mudar. | 02: contrato `src/evaluation/recortes_avaliacao_v1.json`; q008 fica fora, q023 contribui só pela norma e q030 pelas duas recuperações. Não muda runtime nesta etapa. |
| RAG — recusas | `fora_de_escopo` mede taxa de redirecionamento correto para o escopo UsiEdu, com zero chamada de RAG/agentes. `sem_resposta` mede recusa honesta e ausência de fonte inventada. O racional é não premiar uma resposta RAG que não deveria ocorrer. | Rever ao alterar RF-10/RF-14, guardrails ou exemplos de fronteira. | 02 e 06: assertivas e relatórios separados estão definidos no contrato T02.3; não contam no agregado RAG e não alteram o runtime. |
| RAG — regressão | O gate v1 não aceita queda em nenhuma das quatro métricas nem nova falha determinística nas categorias especiais. Baseline e candidato devem ter exatamente os mesmos hashes de dataset, manifest e contrato, a mesma taxonomia, mecanismo e ordem de subperguntas. Fixtures de autoensaio usam `evidence_kind=gate_self_test` e não podem ser apresentados como avaliação real. | Rever após o primeiro candidato real ou aprovação explícita de tolerância estatística. | 02: T02.4 implementa comparação local/CI e artefato reproduzível sem alterar o agregado histórico. |
| Juiz | `kimi-k2.7-code`, configurado como modelo de agente no Bicep pelo provedor `opencode-go`, é o candidato provisório a juiz forte; DeepSeek V4 Flash é o comparador econômico. O repositório não configura hoje um juiz independente e não se cria credencial ou provedor novo. | Rever se o provedor/modelo não for suportado, não permitir configuração comparável ou a evidência mostrar inadequação. | 02: T02.5 pode preparar configuração explícita e proveniência do juiz, além da validação de paridade. |
| Juiz — protocolo | Comparar no mesmo dataset, corpus/manifest, recorte, prompts e métricas; executar três repetições; usar temperatura 0 quando o provedor/modelo suportar o parâmetro; registrar versão, parâmetros, duração, divergência e custo observado/estimado. Interromper antes de exceder US$ 5 por execução comparativa completa. | Rever após a primeira comparação ou mudança de dataset/modelo. | 02: a execução externa para em configuração explícita do juiz, credencial autorizada, acesso ao provedor e custo observável/estimável; isso não bloqueia T02.1–T02.4. |
| Entrega — identidade | GitHub→Azure usará OIDC federado, com RBAC de menor privilégio e GitHub Environment `production` com aprovação manual. Nenhuma credencial Azure persistente pode ser secret. O racional é reduzir exposição e exigir aprovação humana antes do ambiente público. | Rever depois de validar identidade federada, escopo RBAC e aprovadores reais. | 03: desenho de pipeline/runbook pode avançar; criação e teste param no acesso Azure. |
| Entrega — imagem | Trivy é o scanner. Achados CRITICAL e HIGH com correção disponível bloqueiam promoção. Exceção deve ser versionada, justificada, ter dono e validade máxima de 30 dias. | Rever após primeiro scan real ou mudança de política de risco. | 03: política e testes de regra podem avançar; scan de imagem/CI depende de runner e imagem autorizados. |
| Entrega — rollback | Rollback reutiliza digest ou revisão anterior validada, sem reconstruir. Como o Bicep usa `activeRevisionsMode: Single`, antes de automatizar deve haver experimento/runbook nesse modo e preservação do digest anterior. | Rever após experimento Azure bem-sucedido ou alteração do modo de revisões. | 03: rascunho do runbook pode avançar; execução para sem acesso Azure e revisão/digest anterior validada. |
| Segurança — segredos | Azure Key Vault + Managed Identity é o destino de segredos e identidade. A dependência operacional de ACR admin só é eliminada após migração validada de pull e permissões mínimas. O Bicep e o script atuais ainda usam admin/segredos, o que é baseline, não confirmação de migração. | Rever após validação Azure de MI, RBAC e continuidade de JWT. | 04: inventário e plano de migração podem avançar sem valores; aplicação depende de acesso Azure. |
| Segurança — LGPD | Sem controlador jurídico identificado, canal formal, política e retenção aprovados, o piloto fica limitado a contas demo e dados sintéticos; não recebe usuários externos ou dados pessoais. Novos campos de telemetria só podem ter revisão, timestamps e status; pergunta/resposta, token, senha, JWT e identificadores pessoais são vedados. O LangSmith existente exige auditoria antes de ampliar payloads. | Rever somente com fatos jurídicos aprovados. | 04: minimização e conteúdo local podem avançar; publicar política ou ampliar público para nesses fatos. |
| Continuidade | RPO provisório de 24 h e RTO provisório de 4 h para PostgreSQL e Qdrant. São objetivos de piloto, não SLA. | Rever após primeiro restore isolado, mudança de arquitetura ou requisito de produto. | 04: runbook/protocolo e medição podem avançar; aceite final exige evidência de restore. |
| Alertas e custo | Alertas técnicos usam GitHub issue/Action e Azure Monitor; não se inventa e-mail ou Teams. Deve-se reutilizar orçamento Azure somente se ele for factual; sem isso, o teto financeiro permanece parametrizável e não bloqueia testes técnicos. | Rever com acesso à assinatura e aprovação de canal/orçamento. | 04: testes técnicos podem avançar; limiar financeiro real depende de orçamento verificado. |
| Performance — SLO e carga | SLO mensal provisório de 99%: transações sintéticas de login demo + chat final bem-sucedidas ÷ tentativas fora de manutenção documentada. A fonte será Azure Monitor e/ou GitHub Action quando configurados; até lá é não mensurável, não uma alegação de conformidade. Carga: cinco usuários concorrentes e rajada de dez. | Rever após T05.1/T05.2 ou mudança relevante de tráfego/arquitetura. | 05: protocolo e comparação podem usar a carga; não define ainda SLO de primeira resposta/chat. |
| Performance — limites | Cold start de login ≤180 s e `/health` aquecido p95 ≤500 ms, coerentes com P0 (login ~95 s; health 45–212 ms). T05.1 mede primeira resposta/chat antes de fixar seu SLO, pois não há baseline suficiente. | Rever após baseline repetível. | 05: medição pode avançar; nenhum número de chat é alegado antes da evidência. |
| Performance — falhas | No máximo um retry com exponential backoff+jitter apenas para operação idempotente. Não há retry automático após começo de stream ou escrita não idempotente. | Rever após matriz de falhas e testes negativos. | 05: matriz/testes podem ser definidos; mudança de runtime permanece P2. |
| Performance — probes | Readiness é rasa: processo, configuração e modelos carregados. Estado de LLM, Qdrant e PostgreSQL vai para telemetria separada; endpoint adicional só existe após contrato em `docs/09`. Readiness não depende diretamente dessas dependências, para evitar flapping. | Rever somente com exigência de plataforma comprovada. | 05: semântica e testes podem ser definidos; alteração de probe continua P2. |
| Produto — domínio | Pergunta genérica segura fora do domínio é redirecionada ao escopo UsiEdu sem RAG/agentes. Operação determinística aprovada usa `tool`. Conhecimento geral irrestrito não é oferecido. | Rever com requisito de produto aprovado e casos de fronteira testados. | 06: casos e aceite podem ser especificados; comportamento não é implementado nesta etapa. |
| Produto — acessibilidade | Viewports: 360, 768 e 1280 px. WCAG 2.2 AA é referência para fluxos principais, verificando teclado, foco, nome acessível e contraste. É referência de auditoria, não certificação. | Rever se personas, dispositivos ou norma aplicável mudarem. | 06: roteiro de auditoria pode avançar. |
| Produto — publicação | Screenshot de `/insights` pode ser publicado após revisão em sessão segura. Canal de contato exige destino aprovado; vídeo exige host, roteiro final e licença. | Rever quando os fatos e aprovações existirem. | 06: screenshot seguro e material local podem avançar; cada publicação para apenas no seu gate. |

## Pendências factuais remanescentes

| Pendência | Onde a execução para |
|---|---|
| Credencial autorizada e acesso ao `opencode-go`, com custo observável/estimável | Antes das chamadas externas comparativas de T02.5. |
| Fonte institucional autorizada | Antes de ingestão/publicação de corpus em T02.2. |
| Acesso Azure, identidade federada, RBAC e aprovadores do Environment | Antes de criar/testar OIDC, Key Vault/MI, alertas e rollback reais. |
| Revisão/digest anterior validada | Antes do experimento de rollback em modo Single. |
| Controlador, canal formal, política/retenção LGPD | Antes de política pública, usuários externos ou dados pessoais. |
| Orçamento Azure factual | Antes de ativar alerta financeiro com limiar concreto. |
| Medições Azure de primeira resposta/chat e restore | Antes de fixar SLO de chat e de aceitar RPO/RTO. |
| Destino de contato | Antes de publicar o canal de contato. |
| Host, roteiro final e licença | Antes de publicar o vídeo/mídia. |

## Não conclusão

As tarefas P1/P2 continuam não iniciadas. Este registro é somente a decisão
documental exigida para que as microtarefas possam avançar com limites claros.
