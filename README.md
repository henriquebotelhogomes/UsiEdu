# UsiEdu

> Plataforma multi-agente de IA conversacional para a jornada do estudante e do colaborador.
>
> **Projeto piloto — candidatura Engenheiro(a) de IA | Cruzeiro do Sul Educacional**

## Visão Geral

A UsiEdu é uma plataforma unificada de agentes de IA que atende dois públicos:

- **Estudantes**: assistente de jornada acadêmica (dúvidas acadêmicas e financeiras resolvidas por agentes colaboradores).
- **Funcionários/Docentes**: assistente de conhecimento institucional (normas, políticas, processos internos com citação de fonte).

## Arquitetura

```
┌──────────────────────────────────────┐
│       Frontend (React + Vite)        │
└──────────────┬───────────────────────┘
               │ REST/WebSocket
┌──────────────▼───────────────────────┐
│        API Gateway (FastAPI)         │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│   Orquestrador Supervisor (LangGraph)│
└──┬───────┬───────┬───────┬──────────┘
   │       │       │       │
 Acadê- Finan-  Tutor  Documental/
  mico   ceiro  (F2)  Processos (F2)
               │
┌──────────────▼───────────────────────┐
│   Infraestrutura Compartilhada       │
│   RAG · Qdrant · LangSmith · MCP    │
└──────────────────────────────────────┘
```

Detalhes completos na documentação (`docs/`).

## Quickstart

### Pré-requisitos

- Python 3.12+
- Node.js 20+
- Docker e Docker Compose

### Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/<seu-usuario>/usiedu.git
cd usiedu

# 2. Crie o ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# 3. Instale as dependências
pip install -e .

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas chaves (OPENCODE_GO_API_KEY, LANGSMITH_API_KEY, JWT_SECRET)

# 5. Suba o Qdrant
docker compose up -d qdrant
```

### Desenvolvimento

```bash
# Subir todos os serviços (Qdrant + API + frontend)
powershell -File scripts/dev.ps1        # Windows
make dev                                # Linux/macOS

# Rodar testes
pytest

# Lint e formatação
ruff check .
ruff format .

# Ingerir documentos na base de conhecimento
python -m src.rag.ingest

# Rodar a API
uvicorn src.api.main:app --reload
```

## Deploy público — Azure Container Apps

O deploy do piloto está preparado para **Azure Container Apps**, usando a
assinatura Azure for Students. A URL pública é criada pelo Azure durante o
provisionamento e é exibida ao final do script; registre-a aqui após a primeira
execução.

> URL pública: **pendente de primeiro deploy**

### Pré-requisitos

- Azure CLI instalado e autenticado: `az login`.
- Docker Desktop em execução.
- Assinatura **Azure for Students** selecionada: `az account set --subscription "<nome-ou-id>"`.
- Chaves do OpenCode Go e LangSmith disponíveis. Elas são solicitadas sem eco
  pelo script e não são gravadas no repositório.

No PowerShell, execute:

```powershell
.\infra\azure\deploy.ps1 `
  -ResourceGroup rg-usiedu `
  -Prefix usiedu `
  -Location brazilsouth `
  -ImageTag v1
```

O script cria um Azure Container Registry Basic, publica as imagens API e
frontend, provisiona Container Apps + Azure Files e gera um `JWT_SECRET` novo
se ele não for informado. Guarde esse segredo em um gerenciador de senhas; não
reutilize a chave de desenvolvimento e não o inclua em `.env` versionado.

Depois do deploy, execute a ingestão inicial e acompanhe o resultado:

```powershell
az containerapp job start --name usiedu-ingest --resource-group rg-usiedu
az containerapp job execution list --name usiedu-ingest --resource-group rg-usiedu
```

Use a URL impressa pelo script para validar `https://<url>/health`, login com
`ana@demo.usiedu` / `estudante123`, chat, feedback e `/insights`. O frontend é
a única origem pública; API e Qdrant permanecem na rede interna do ambiente.

O frontend e a API podem escalar a zero para economizar crédito. Por isso, após
inatividade, a primeira abertura ou resposta pode levar **até 60 segundos**
(cold start). O Qdrant permanece em uma réplica para preservar disponibilidade
do RAG; acompanhe o consumo em **Cost Management** e crie um alerta de orçamento
antes da exposição pública.

## Frontend e Landing Page

O frontend (React + Vite + TypeScript, com `react-router-dom`) tem três rotas:

| Rota | Tela | Acesso |
|---|---|---|
| `/` | **Landing page institucional** | público |
| `/login` | Login (usuários demo visíveis na tela) | público |
| `/chat` | Chat com os agentes (fontes citadas, agente que respondeu) | autenticado |

No chat, cada resposta traz botões **👍/👎 (human-on-the-loop)**: o feedback é
persistido em SQLite, anexado ao trace correspondente no LangSmith e agregado
em `GET /feedback/stats` (taxa de satisfação).

A landing page apresenta o projeto para avaliadores/visitantes:

- **Hero** com imagem de campus e chamadas para o login e o repositório.
- **Menus de navegação** para as seções: Funcionalidades (estudante/funcionário), Agentes (Acadêmico, Financeiro, Documental + Tutor na Fase 2), Arquitetura (diagrama do grafo supervisor), Fontes e Stack.
- **Fontes da base de conhecimento**: download dos PDFs usados no RAG (Regimento Geral e Calendário 2026.2 da UnB) e links oficiais dos documentos HTML (Guia do Servidor, LDB).
- **Links externos** para a [documentação técnica](https://henriquebotelhogomes.github.io/UsiEdu/) (MkDocs) e para o repositório no GitHub.

Os documentos da seção Fontes ficam em `frontend/public/documentos/` (cópias dos
arquivos indexados de `knowledge_base/`, que é recriada por `python -m src.rag.download`).

## Screenshots

**Landing page** — apresentação institucional com funcionalidades, agentes, arquitetura, fontes e stack:

![Landing page](screenshots/landing-page.png)

**Chat como estudante** — pergunta sobre feriados respondida com citação das fontes (Agente Acadêmico):

![Chat estudante](screenshots/chat-estudante.png)

**Chat como funcionário** — licença capacitação respondida pelo Agente Documental com base no Guia do Servidor:

![Chat funcionário](screenshots/chat-funcionario.png)

**Documentação técnica** — MkDocs Material publicada no GitHub Pages:

![Documentação MkDocs](screenshots/docs-mkdocs.png)

Para regenerar os prints com o sistema rodando localmente: `python scripts/capture_screenshots.py`
(requer `pip install playwright && python -m playwright install chromium`).
Após o deploy, use a mesma rotina contra HTTPS:
`python scripts/capture_screenshots.py --base-url https://<url-publica>`.

## API

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| POST | `/auth/login` | não | Autentica e retorna JWT |
| POST | `/chat` | sim | Envia mensagem, recebe resposta com fontes e agentes envolvidos |
| POST | `/feedback` | sim | Registra avaliação 👍/👎 da resposta (human-on-the-loop) |
| GET | `/feedback/stats` | sim | Métricas agregadas de satisfação |
| GET | `/health` | não | Liveness check |

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12+, FastAPI, LangGraph, LangChain |
| LLM | OpenCode Go (DeepSeek V4 Flash + Kimi K2.7 Code) |
| Vector DB | Qdrant (Docker) |
| Embeddings | FastEmbed / sentence-transformers (local, ONNX) |
| Reranker | bge-reranker-base (local) |
| Observabilidade | LangSmith |
| Frontend | React + Vite + TypeScript + react-router-dom |
| Qualidade | Ruff, pytest, GitHub Actions |
| Documentação | MkDocs Material |

## Documentação

A documentação completa está em `docs/`:

| Documento | Conteúdo |
|---|---|
| `01-visao-geral-arquitetura.md` | Visão, personas, arquitetura |
| `02-agentes-e-orquestracao.md` | Agentes, grafo LangGraph, fluxos A2A |
| `03-rag-e-infraestrutura.md` | Pipeline RAG, vector DB, MCP, memória |
| `04-piloto-e-roadmap.md` | Escopo, critérios de aceite, roadmap |
| `05-fontes-base-conhecimento.md` | Catálogo de fontes abertas (UnB) |
| `06-visao-escala-global.md` | Gap analysis para escala global |
| `07-prd-requisitos.md` | PRD: requisitos funcionais e não-funcionais |
| `08-plano-execucao.md` | Sprints, tarefas e Definition of Done |
| `09-contratos-tecnicos.md` | API, env vars, modelos de dados, convenções |

## Licença

MIT — ver [LICENSE](LICENSE).
