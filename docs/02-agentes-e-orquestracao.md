# Agentes e Orquestração

> Detalha o funcionamento interno dos agentes, o grafo LangGraph do Supervisor,
> o estado compartilhado e os fluxos de colaboração entre agentes (A2A).

---

## 1. O Grafo Supervisor (LangGraph)

O coração da plataforma é um **grafo supervisor** implementado em LangGraph.
Cada conversa é uma execução do grafo com estado compartilhado.

### 1.1 Estrutura do grafo

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           ▼
                  ┌──────────────────┐
                  │  supervisor_node │  ← classifica intenção,
                  │  (roteamento)    │    monta plano se necessário
                  └────────┬─────────┘
                           │ (aresta condicional)
        ┌──────────┬───────┼────────┬─────────────┐
        ▼          ▼       ▼        ▼             ▼
  ┌──────────┐ ┌────────┐ ┌─────┐ ┌──────┐ ┌────────────┐
  │academico │ │finance-│ │car- │ │tutor │ │documental/ │
  │  _node   │ │iro_node│ │reira│ │_node │ │ processos  │
  └────┬─────┘ └───┬────┘ └──┬──┘ └──┬───┘ └─────┬──────┘
       │           │         │       │           │
       └───────────┴────┬────┴───────┴───────────┘
                        ▼
              ┌───────────────────┐
              │ consolidation_node│  ← consolida resultados,
              │ (consolidação)    │    aplica guardrails
              └────────┬──────────┘
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
   precisa de mais info?      ┌────────┐
   sim → volta ao             │  END   │
   supervisor_node            └────────┘
   (ciclo)
```

**Pontos-chave:**
- **Fluxo cíclico**: se a consolidação detectar resposta incompleta (ex.: só o Financeiro respondeu a uma pergunta que também era acadêmica), o grafo volta ao supervisor — requisito central do LangGraph citado na vaga.
- **Delegação paralela**: para perguntas compostas, o supervisor dispara agentes independentes em paralelo (asyncio) e consolida ao final.
- **Guardrails na consolidação**: verificação de citação de fontes e filtro de conteúdo fora de escopo antes de responder.

### 1.2 Estado compartilhado (`AgentState`)

```python
class AgentState(TypedDict):
    user_id: str
    profile: Literal["student", "staff"]      # controla quais agentes estão disponíveis
    messages: Annotated[list, add_messages]   # histórico da conversa
    plan: list[str] | None                    # plano (perguntas compostas)
    delegations: list[Delegation]             # quem foi acionado e por quê
    agent_results: dict[str, AgentResult]     # resultados parciais por agente
    retrieved_sources: list[Source]           # fontes RAG usadas (para citação)
    needs_more_info: bool                     # alimenta a aresta cíclica
```

### 1.3 Persistência e memória

| Necessidade | Mecanismo LangGraph |
|---|---|
| Retomar conversa (contexto de sessão) | `Checkpointer` (SQLite no piloto, Postgres em produção) |
| Memória de longo prazo entre sessões | `Store` persistente (perfil de aprendizado do aluno, preferências) |
| Auditoria de delegações | Campo `delegations` no estado + tracing |

---

## 2. Padrões de Raciocínio (Agentic AI)

### 2.1 ReAct — delegação simples

Para perguntas de intenção única, o supervisor age no padrão **ReAct**:
1. **R**eason: classifica a intenção (acadêmica/financeira/carreira/estudo/institucional).
2. **Act**: chama o agente especialista correspondente.
3. **Observe**: valida o resultado e consolida.

### 2.2 Plan-and-Solve — perguntas compostas

Para perguntas que atravessam domínios:
1. **Plan**: o supervisor decompõe a pergunta em sub-tarefas numeradas.
2. **Solve**: executa as sub-tarefas (em paralelo quando independentes).
3. **Consolidate**: sintetiza uma resposta única e coerente.

**Exemplo real:**
> "Estou com dificuldade em Cálculo I e não sei se pago a disciplina de novo ou pego dependência."

Plano gerado:
1. `[academico]` Consultar regras de dependência e histórico do aluno.
2. `[financeiro]` Calcular custo de cada opção (repetir vs. dependência).
3. `[academico+tutor]` Verificar alternativas pedagógicas (monitoria, reforço).

---

## 3. Comunicação entre agentes (A2A)

### 3.1 Fase piloto: delegação in-process

No piloto, os agentes são **nós do grafo** comunicando-se via estado compartilhado — simples de demonstrar e depurar.

### 3.2 Fase 3: protocolo A2A (Google)

Cada agente especialista vira um **A2A Agent** independente, com:
- **Agent Card**: metadados declarando capacidades (descoberta dinâmica).
- **Tasks**: o supervisor envia tarefas; agentes podem responder, pedir esclarecimento ou delegar adiante.
- Benefício: agentes implantáveis e escaláveis separadamente; novos agentes entram na plataforma sem alterar o supervisor.

```
┌────────────┐   A2A task   ┌──────────────────┐
│ Supervisor │ ───────────► │ Agente Acadêmico│
│ (client)   │ ◄─────────── │ (A2A server)     │
└────────────┘   artifact   └──────────────────┘
```

---

## 4. Especificação por Agente

### 4.1 Supervisor

| Item | Especificação |
|---|---|
| Modelo | Gemini (rápido, para classificação) |
| Entrada | Mensagem do usuário + perfil + histórico |
| Saída | Decisão de roteamento OU plano de sub-tarefas |
| Guardrails | Lista branca de domínios; fora do escopo → resposta padrão educada |
| Temperatura | Baixa (~0.1) — roteamento determinístico |

### 4.2 Agente Acadêmico

| Item | Especificação |
|---|---|
| Ferramentas | `search_regimento`, `search_calendario`, `get_notas(aluno)`, `get_faltas(aluno)`, `get_matricula(aluno)` |
| Fonte de verdade | Somente documentos recuperados via RAG + APIs mockadas |
| Formato de saída | Resposta + lista de fontes (documento, seção) |
| Comportamento sem fonte | Declara "não encontrei essa informação nos documentos oficiais" e sugere canal humano |

### 4.3 Agente Financeiro

| Item | Especificação |
|---|---|
| Ferramentas | `get_boletos(aluno)`, `simular_renegociacao(boleto_id, opcoes)`, `get_politica_descontos()` |
| Restrição | Nunca promete desconto fora das regras da política recuperada |
| Sensibilidade | Dados financeiros mascarados no log/tracing (LGPD) |

### 4.4 Agente de Carreira *(roadmap)*

| Item | Especificação |
|---|---|
| Ferramentas | `search_eventos(curso)`, `search_estagios(curso)`, `get_programas_bolsa()` |

### 4.5 Tutor Pedagógico *(roadmap)*

| Item | Especificação |
|---|---|
| Ferramentas | `search_material(disciplina)`, `gerar_quiz(tópicos, nível)`, `get_plano_estudo(aluno)` |
| Memória de longo prazo | Armazena: tópicos com dificuldade, erros em quizzes, estilo preferido de explicação |
| Personalização | System prompt montado dinamicamente com o perfil recuperado do Store |

### 4.6 Agente Documental

| Item | Especificação |
|---|---|
| Ferramentas | `search_politicas(tema)`, `search_manuais(tema)`, `search_faq(tema)` |
| Precisão | Recuperação híbrida (vetor + BM25) + reranking |
| Obrigatoriedade | Toda afirmação normativa precisa de citação |

### 4.7 Agente de Processos *(roadmap)*

| Item | Especificação |
|---|---|
| Ferramentas | Via **MCP server**: `listar_processos`, `detalhar_processo(id)`, `abrir_solicitacao(tipo, dados)` |
| Dado estruturado | SQLite no piloto — MCP evita indexar dados tabulares no vector DB |

---

## 5. Fluxos de exemplo (sequência)

### 5.1 Estudante — pergunta composta (acadêmico + financeiro)

```
Aluno: "Perdi o prazo de matrícula em Cálculo. E agora? Quanto custa?"

1. supervisor_node  → classifica como composta → plano:
      [academico: opções após perda de prazo]
      [financeiro: custos de matrícula fora de prazo]
2. academico_node   → RAG(regimento) → "matrícula extemporânea até dia X, via requerimento"
3. financeiro_node  → get_politica → taxa de requerimento: R$ Y
4. consolidation    → resposta única com passos + valores + fontes
```

### 5.2 Funcionário — pergunta institucional

```
Carlos: "Posso aplicar avaliação substitutiva para aluno com atestado?"

1. supervisor_node  → perfil staff → documental_node
2. documental_node  → RAG(regimento docente, busca híbrida)
3. consolidação     → resposta citando regimento (artigo/página)
```

### 5.3 Fora de escopo (guardrail)

```
Aluno: "Me ajuda com a lição de Física?"
1. supervisor_node → intenção fora da lista branca
2. resposta padrão: "Esse assunto foge do meu escopo. Para apoio pedagógico,
   procure a monitoria do seu curso."  (no roadmap, o Tutor assumiria casos assim)
```

---

## 6. Decisões em aberto *(para revisão)*

- [x] Nome oficial do produto: **UsiEdu**.
- [ ] Perfil de estudante no piloto: dados 100% mockados ou dataset sintético realista?
- [x] Tracing: **LangSmith** (cloud, free tier).
- [ ] Incluir interface visual Langflow como demo de prototipação rápida (requisito da vaga) — opcional, pode ser um fluxo espelho do RAG.
