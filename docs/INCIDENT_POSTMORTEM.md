# 📋 Template Canônico de Postmortem Blameless (SRE & Confiabilidade)

> **UsiEdu Incident Management — Cultura Justa & Aprendizado Contínuo**  
> Todo incidente de severidade alta (SEV-1 / SEV-2) deve gerar um postmortem concluído em até 72h.

---

## 1. Informações Básicas
* **Título do Incidente:** [Ex: Degradação no Nó Supervisor devido a Rate Limit no Provedor de LLM]
* **Data do Incidente:** YYYY-MM-DD
* **Duração Total:** X horas e Y minutos
* **Severidade:** SEV-1 (Indisponibilidade Crítica) / SEV-2 (Degradação Severa) / SEV-3 (Impacto Menor)
* **Incident Commander (IC):** @nome
* **Lead de Resolução:** @nome
* **Serviços Afetados:** API FastAPI, LangGraph Engine, Qdrant Hybrid Search, Frontend Web

---

## 2. Resumo Executivo
*Breve descrição do que aconteceu, qual foi o impacto para estudantes/servidores universitários e como o sistema foi restaurado.*

---

## 3. Impacto no Negócio & Error Budget
* **Usuários Afetados:** Estimativa de estudantes ou servidores com erro na sessão.
* **Queima de Error Budget:** X% consumido nas últimas 24h (SLO de disponibilidade alvo: 99.5%).
* **Taxa de Erro de API:** Pico de X% de respostas HTTP 5xx.
* **Latência p95 / p99:** Degradação de X ms para Y ms.

---

## 4. Linha do Tempo (Horário de Brasília - UTC-3)
* `HH:MM` — Detecção automática do alerta no Datadog Pro (`HighErrorRateFastAPI`).
* `HH:MM` — Abertura da sala de incidente e investigação inicial.
* `HH:MM` — Identificação da causa raiz no provedor ou nó do grafo.
* `HH:MM` — Execução do rollback automatizado via workflow GitHub Actions (`rollback-azure.yml`) ou ativação do fallback de LLM.
* `HH:MM` — Recuperação dos probes de liveness e prontidão (`/health`).
* `HH:MM` — Incidente encerrado e retorno aos níveis normais de SLO.

---

## 5. Análise de Causa Raiz (Os 5 Porquês)
1. **Por que o chat parou de responder?** Porque o nó supervisor gerou exceção não tratada ao chamar o LLM.
2. **Por que gerou exceção?** Porque o endpoint retornou HTTP 429 (Too Many Requests).
3. **Por que retornou 429?** Porque houve um pico de perguntas de rematrícula que superou o limite do provedor primário.
4. **Por que o fallback não assumiu?** Porque a hierarquia de contingência no AI Gateway não estava ativada.
5. **Por que não estava ativada?** Porque o roteador operava com dependência direta sem retries com exponential backoff.

---

## 6. O que Funcionou Bem vs. O que Falhou
### O que funcionou bem:
- Os alertas do Datadog Pro dispararam dentro de 60 segundos após o início da falha.
- O checkpointer `AsyncSqliteSaver` manteve o histórico das conversas sem corrupção de dados.

### Onde falhamos:
- Falta de fallback automático transparente para o segundo provedor de LLM.
- Mensagem de erro genérica exibida no frontend em vez de aviso amigável de sobrecarga temporária.

---

## 7. Ações Corretivas e Preventivas (Action Items)

| ID | Ação Corretiva | Tipo | Responsável | Prazo | Status |
|:---:|---|:---:|:---:|:---:|:---:|
| `ACT-01` | Configurar hierarquia de fallback no LiteLLM Proxy | Prevenção | @engenharia | YYYY-MM-DD | Pendente |
| `ACT-02` | Implementar retry exponencial no nó Supervisor do LangGraph | Mitigação | @engenharia | YYYY-MM-DD | Pendente |
| `ACT-03` | Adicionar probe de contingência no dashboard Datadog | Detecção | @sre | YYYY-MM-DD | Pendente |
