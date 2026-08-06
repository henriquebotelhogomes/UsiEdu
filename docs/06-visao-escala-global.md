# Visão de Escala Global — Gap Analysis

> Exercício estratégico: se a UsiEdu evoluísse de projeto piloto para uma **startup global**
> de IA conversacional para educação, o que faltaria em tecnologia, arquitetura, segurança,
> testes, observabilidade e documentação?
>
> Este documento **não** faz parte do escopo do piloto — demonstra visão de produto e
> maturidade de engenharia de longo prazo.

---

## 1. Arquitetura e Infraestrutura

| Gap | Piloto | Escala global |
|---|---|---|
| Orquestração de containers | Docker Compose | **Kubernetes (Rancher)** com autoscaling horizontal por agente (HPA/KEDA) |
| Provisionamento | Manual | **IaC com Terraform** + GitOps (ArgoCD) |
| Deploy | Local | CI/CD (GitHub Actions) com **canary/blue-green**, ambientes dev/staging/prod |
| Multi-região | Não | Deploy multi-região ativo-ativo; roteamento geo-DNS; conformidade de residência de dados (dados de alunos brasileiros ficam no Brasil — LGPD) |
| Processamento assíncrono | Não | **Filas/eventos** (Celery+Redis ou Kafka): ingestão de documentos, avaliações, notificações |
| Multi-tenancy | Perfis simples | Isolamento por tenant (escolas/grupos educacionais): dados, coleções vetoriais e modelos por tenant |
| Resiliência de LLM | Provider único | **LLM Gateway** com fallback entre providers, circuit breaker, rate limiting e retry com backoff |
| Latência/custo | Sem cache | **Cache semântico** (LangCache/GPTCache) para perguntas repetidas; streaming (SSE) como padrão |
| Dados | SQLite | **PostgreSQL** gerenciado com réplicas, backups automáticos, migrações (Alembic), plano de DR com RPO/RTO definidos |
| Frontend | Vite dev server | CDN, build otimizado, i18n (pt-BR, en, es) para expansão global |

## 2. Segurança

| Gap | Piloto | Escala global |
|---|---|---|
| Autenticação | JWT simples | **OIDC/SSO corporativo** (integração com Google Workspace/Entra ID das instituições) |
| Autorização | Perfil estudante/staff | **RBAC/ABAC** granular: permissões por papel, curso, unidade |
| Conformidade | Menção a LGPD | **Programa LGPD/GDPR completo**: consentimento, direitos do titular (acesso/retificação/exclusão), retenção e expurgo automático, DPO, registro de tratamento; trilha para **SOC 2 / ISO 27001** |
| IA adversarial | Guardrails de escopo | Defesa contra **prompt injection e jailbreak**: sanitação de entrada, filtros de saída, sandbox de tools, avaliação adversarial contínua (**red teaming** de LLM) |
| Dados sensíveis | Dados mockados | **Mascaramento de PII** (ex.: Presidio) antes de enviar ao LLM; criptografia em trânsito (TLS 1.3) e em repouso; chaves gerenciadas (KMS) |
| Segredos | .env | **HashiCorp Vault** ou gerenciador cloud; rotação automática |
| Supply chain | Sem verificação | SCA de dependências (Dependabot/Snyk), SAST/DAST no CI, scan de containers, SBOM |
| Auditoria | Logs básicos | **Audit trail imutável** de ações de agentes (quem autorizou o quê), essencial quando agentes executam ações em sistemas acadêmicos |

## 3. Testes

| Gap | Piloto | Escala global |
|---|---|---|
| Avaliação de LLM | Ragas pontual | **Pipeline contínuo de eval no CI**: dataset golden versionado, gates de regressão (merge bloqueado se faithfulness cair), comparação A/B de prompts/modelos |
| Segurança de IA | Não | Suíte de **ataques adversariais** automatizada (injection, vazamento de contexto, extração de prompt de sistema) |
| Performance | Não | Testes de carga (**k6/Locust**): p95 de latência, concorrência, custo por conversa sob pico (matrículas!) |
| E2E | Demo manual | **Playwright** cobrindo fluxos críticos de ambos os perfis |
| Contrato | Não | Testes de contrato entre API e frontend + versionamento de API (semver) |
| Caos | Não | Chaos engineering: queda de provider de LLM, vector DB indisponível — validar degradação graciosa |
| Ambientes | Local | **Staging espelhando produção** com dados sintéticos realistas |

## 4. Observabilidade

| Gap | Piloto | Escala global |
|---|---|---|
| Padrão | LangSmith + Grafana | **OpenTelemetry** unificando traces entre frontend, API, agentes e LLM |
| Alerting | Não | **SLOs e error budgets** com alertas escalonados (PagerDuty/Opsgenie); plantão on-call com playbooks |
| Negócio | Não | Métricas de produto: **deflection rate** (% resolvido sem humano), CSAT por resposta, retenção, custo por conversa resolvida |
| FinOps de IA | Não | Dashboard de **custo por tenant/agente/modelo**, orçamentos de tokens, detecção de explosão de consumo |
| Qualidade em produção | Não | Amostragem de conversas reais → eval automático + revisão humana; **feedback loop** para melhoria de prompts e do dataset golden |
| Anomalias | Não | Detecção de drift (mudança no padrão de perguntas), alucinação em alta, latência degradada |

## 5. Governança de IA (categoria extra, crítica para startups de IA)

- **Registro de modelos**: versão de prompts, modelo, dataset de eval e métricas por release.
- **Human-in-the-loop**: transbordo para atendente humano com handoff contextual quando confiança é baixa ou o tema é sensível (financeiro, disciplinar).
- **IA responsável**: revisão de viés em respostas, moderação de conteúdo, transparência ("você fala com uma IA" + fontes citadas).
- **Controle de ações**: políticas de quais ações agentes podem executar sozinhos vs. exigir aprovação humana (autonomia progressiva).

## 6. Documentação

| Gap | Piloto | Escala global |
|---|---|---|
| Decisões | Implícitas | **ADRs** (Architecture Decision Records) para toda decisão relevante |
| Operação | README | **Runbooks** por incidente + guias de on-call; post-mortems sem culpa |
| API | OpenAPI interno | Portal público de API versionada para integrações (ERPs, CRMs educacionais) |
| Produto | Não | Central de ajuda do usuário final, changelog público, guias de integração para instituições |
| Comercial/legal | Não | SLAs por plano, DPA (acordo de tratamento de dados), whitepaper de segurança |

## 7. Como usar este documento na candidatura

Na apresentação do piloto, dedicar **1 minuto final** a este mapa:
> "O que está entregue é uma fatia vertical funcional. Este gap analysis mostra como eu
> escalaria a UsiEdu para produção global — segurança, multi-tenancy, avaliação contínua e
> observabilidade já estão desenhadas, prontas para serem executadas em fases."

Isso demonstra senioridade: entregar o piloto enxuto **e** enxergar o produto completo.
