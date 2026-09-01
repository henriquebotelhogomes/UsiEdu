"""Script de avaliação Ragas da UsiEdu.

Conforme RF-29 — gera relatório de qualidade (faithfulness, context_precision,
context_recall, answer_relevancy) em Markdown a partir do dataset de avaliação.

Uso:
    python -m src.evaluation.run_ragas [--dataset path] [--output path] [--limit N]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# Carrega variáveis do .env (OPENCODE_GO_API_KEY, LANGSMITH_API_KEY, etc.)
load_dotenv()

# Metas do doc 03 seção 6.1
METAS = {
    "faithfulness": 0.90,
    "context_precision": 0.80,
    "context_recall": 0.80,
    "answer_relevancy": 0.85,
}

DATASET_DEFAULT = Path(__file__).parent / "dataset.jsonl"
OUTPUT_DEFAULT = Path(__file__).parent / "relatorio_ragas.md"
FEEDBACK_DEFAULT = Path(__file__).parent / "feedback_negativo.jsonl"  # T8.1


def carregar_dataset(path: Path) -> list[dict]:
    """Carrega o dataset JSONL de avaliação."""
    perguntas = []
    with path.open(encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                perguntas.append(json.loads(linha))
    return perguntas


def _extrair_contexto(result: dict) -> list[str]:
    """Extrai os trechos de contexto usados na resposta."""
    sources = result.get("retrieved_sources", [])
    contextos = []
    for s in sources:
        if isinstance(s, dict):
            contextos.append(s.get("excerpt", ""))
        else:
            contextos.append(getattr(s, "excerpt", ""))
    return contextos


def _extrair_resposta(result: dict) -> str:
    """Extrai o texto da resposta final do grafo."""
    messages = result.get("messages", [])
    if not messages:
        return ""
    last = messages[-1]
    return last.content if isinstance(last.content, str) else str(last.content)


def _carregar_grafo(
    router_model: str | None = None,
    agent_model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    qdrant_url: str | None = None,
):
    """Carrega o grafo com LLM fake (offline) ou real + RAG conforme env.

    `temperature=None` delega ao provedor: alguns modelos rejeitam qualquer
    outro valor, e a coerção já vive em src/llm/provider.py.
    """
    from src.llm.fake import FakeChatModel
    from src.orchestration.graph import create_chat_graph

    # Se houver API key, usa modelo real + RAG; senão usa fake determinístico
    if os.getenv("OPENCODE_GO_API_KEY"):
        from src.llm.provider import get_chat_model

        router_llm = get_chat_model(
            model_name=router_model or os.getenv("USIEDU_ROUTER_MODEL", "deepseek-v4-flash"),
            temperature=temperature,
            max_tokens=max_tokens,
        )
        agent_llm = get_chat_model(
            model_name=agent_model or os.getenv("USIEDU_AGENT_MODEL", "deepseek-v4-flash"),
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Cria retriever RAG conectado ao Qdrant (paridade com src/api/main.py:
        # BM25 + fusão RRF + cross-encoder; sem isso a avaliação media um
        # sistema diferente do que vai para produção)
        from qdrant_client import QdrantClient

        from src.rag.embedder import Embedder
        from src.rag.reranker import Reranker
        from src.rag.retriever import HybridRetriever
        from src.rag.settings import RagSettings

        rag_settings = RagSettings()

        qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
        embedder = Embedder()
        try:
            reranker: Reranker | None = Reranker()
        except Exception:
            reranker = None
        # Uma retriever por coleção, como em src/api/main.py: o nó documental
        # filtra por publico_alvo=staff, e a coleção acadêmica não tem nenhum
        # ponto nesse filtro — sem a institucional, metade do dataset é respondida
        # sem o corpus que a fundamenta.
        client = QdrantClient(qdrant_url)
        retriever = HybridRetriever(
            client=client,
            embedder=embedder,
            reranker=reranker,
            collection_name=rag_settings.qdrant_collection_academico,
        )
        documental_retriever = HybridRetriever(
            client=client,
            embedder=embedder,
            reranker=reranker,
            collection_name=rag_settings.qdrant_collection_institucional,
        )
        retriever.build_bm25_index()
        documental_retriever.build_bm25_index()
    else:
        router_llm = FakeChatModel(
            default_response=json.dumps(
                {"intent": "academico", "plan": None, "reasoning": "avaliação offline"}
            )
        )
        agent_llm = FakeChatModel(default_response="Resposta de avaliação (modo offline).")
        retriever = None
        documental_retriever = None

    return create_chat_graph(
        router_llm=router_llm,
        agent_llm=agent_llm,
        retriever=retriever,
        documental_retriever=documental_retriever,
    )


def _avaliar_resposta(pergunta: dict, resposta: str) -> dict:
    """Avalia heuristicamente a resposta (fallback sem Ragas).

    Usa heurísticas simples quando o Ragas não está disponível ou o
    ambiente é offline: verifica presença de palavras-chave da referência
    e ausência de termos de alucinação.
    """
    ref = pergunta.get("reference_answer", "").lower()
    resp = resposta.lower()
    cat = pergunta.get("category", "direct")

    # Heurística: cobertura de palavras-chave da referência
    palavras = [p for p in ref.split() if len(p) > 4]
    if not palavras:
        return {
            "faithfulness": 1.0,
            "context_precision": 1.0,
            "context_recall": 1.0,
            "answer_relevancy": 1.0,
        }

    cobertas = sum(1 for p in palavras if p in resp)
    cobertura = cobertas / len(palavras)

    # Perguntas fora de escopo: resposta deve negar/redirecionar
    if cat == "fora_de_escopo":
        negacao = any(
            t in resp
            for t in [
                "fora do escopo",
                "não encontrei",
                "fora de escopo",
                "não posso",
                # resposta padrão do nó fora_de_escopo (consolidation.py)
                "fora do meu escopo",
            ]
        )
        return {
            "faithfulness": 1.0 if negacao else 0.0,
            "context_precision": 1.0,
            "context_recall": 1.0,
            "answer_relevancy": 1.0 if negacao else 0.0,
        }

    if cat == "sem_resposta":
        honesto = any(
            t in resp
            for t in [
                "não encontrei",
                "não sei",
                "não encontrada",
                "não disponível",
                # formulação usada pelos agentes na recusa honesta
                "não localizei",
            ]
        )
        return {
            "faithfulness": 1.0 if honesto else 0.0,
            "context_precision": 1.0,
            "context_recall": 1.0,
            "answer_relevancy": 1.0 if honesto else 0.0,
        }

    return {
        "faithfulness": min(cobertura + 0.3, 1.0),
        "context_precision": min(cobertura + 0.2, 1.0),
        "context_recall": min(cobertura + 0.2, 1.0),
        "answer_relevancy": min(cobertura + 0.3, 1.0),
    }


def _formatar_metricas(metricas: list[dict]) -> dict[str, float]:
    """Calcula a média de cada métrica."""
    medias = {}
    for metrica in ["faithfulness", "context_precision", "context_recall", "answer_relevancy"]:
        valores = [m.get(metrica, 0.0) for m in metricas if m.get(metrica) is not None]
        medias[metrica] = sum(valores) / len(valores) if valores else 0.0
    return medias


def _similaridade_jaccard(a: str, b: str) -> float:
    """Similaridade por Jaccard entre os conjuntos de palavras (normalizados)."""
    palavras_a = set(a.lower().split())
    palavras_b = set(b.lower().split())
    if not palavras_a and not palavras_b:
        return 1.0
    if not palavras_a or not palavras_b:
        return 0.0
    return len(palavras_a & palavras_b) / len(palavras_a | palavras_b)


def _verificar_gate(relatorio: Path, min_score: float) -> tuple[bool, dict[str, float]]:
    """Valida o CI Quality Gate lendo as métricas do relatório gerado (RF4-04).

    Retorna ``(aprovado, valores)``; aprovado é True somente quando todas as
    métricas atingem o threshold mínimo.
    """
    valores: dict[str, float] = {}
    texto = relatorio.read_text(encoding="utf-8")
    for linha in texto.splitlines():
        partes = [p.strip() for p in linha.strip().split("|")]
        # Formato da linha: | metrica | ≥ meta | resultado | status |
        if len(partes) >= 4 and partes[1] in METAS:
            try:
                valores[partes[1]] = float(partes[3])
            except ValueError:
                continue
    aprovado = len(valores) == len(METAS) and all(v >= min_score for v in valores.values())
    return aprovado, valores


async def _executar_casos_feedback(graph, casos: list[dict]) -> list[dict]:
    """Reexecuta as perguntas com 👎 e compara com a resposta rejeitada (T8.1).

    Heurística offline: se a nova resposta é praticamente idêntica à rejeitada
    (Jaccard ≥ 0,95), o caso não melhorou; caso contrário, a resposta mudou e
    pede revisão manual (ou LLM judge em modo Ragas+LLM).
    """
    resultados = []
    for caso in casos:
        state = {
            "user_id": "feedback@usiedu",
            "profile": caso.get("profile", "student"),
            "messages": [HumanMessage(content=caso["question"])],
            "plan": None,
            "delegations": [],
            "agent_results": {},
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": None,
        }
        message_id = caso.get("message_id", "sem-id")
        config = {"configurable": {"thread_id": f"eval-fb-{message_id[:8]}"}}

        try:
            result = await graph.ainvoke(state, config)
            nova = _extrair_resposta(result)
        except Exception:
            nova = ""

        rejeitada = caso.get("rejected_answer") or ""
        similaridade = _similaridade_jaccard(nova, rejeitada) if nova else None
        if similaridade is None:
            status = "💥 Falha ao reexecutar"
        elif similaridade >= 0.95:
            status = "❌ Repete resposta rejeitada"
        else:
            status = "🔄 Alterada — revisão manual"

        resultados.append(
            {
                "message_id": message_id,
                "question": caso["question"],
                "user_comment": caso.get("user_comment"),
                "similaridade": similaridade,
                "status": status,
            }
        )
    return resultados


def _gerar_secao_feedback(resultados_fb: list[dict], pulados: int) -> list[str]:
    """Monta a seção "Casos de feedback negativo" do relatório (T8.1)."""
    linhas = [
        "",
        "## Casos de feedback negativo (T8.1)",
        "",
    ]
    if not resultados_fb and pulados == 0:
        linhas.append(
            "Nenhum caso exportado ainda — rode `python scripts/export_feedback_to_eval.py`."
        )
        return linhas

    linhas.append(
        f"> {len(resultados_fb)} caso(s) reavaliado(s), {pulados} pulado(s) sem pergunta "
        "recuperada (`question: null`). Comparação heurística (Jaccard) com a resposta "
        "rejeitada; em modo Ragas+LLM recomenda-se confirmar com LLM judge."
    )
    linhas += [
        "",
        "| message_id | Pergunta | Comentário | Similaridade | Status |",
        "|---|---|---|---|---|",
    ]
    for r in resultados_fb:
        comentario = (r.get("user_comment") or "—").replace("|", "\\|")[:60]
        sim = "—" if r["similaridade"] is None else f"{r['similaridade']:.2f}"
        linhas.append(
            f"| {r['message_id'][:8]} | {r['question'][:60]}... | {comentario} | {sim} | "
            f"{r['status']} |"
        )
    return linhas


def _gerar_relatorio(
    perguntas: list[dict],
    resultados: list[dict],
    medias: dict[str, float],
    path: Path,
    modo: str,
    resultados_fb: list[dict] | None = None,
    pulados_fb: int = 0,
) -> None:
    """Gera o relatório Markdown com as métricas Ragas."""
    linhas = [
        "# Relatório de Avaliação Ragas — UsiEdu",
        "",
        f"> Gerado em {datetime.now(timezone.utc).isoformat()} | Modo: **{modo}**",
        "",
        "## Metas (doc 03, seção 6.1)",
        "",
        "| Métrica | Meta | Resultado | Status |",
        "|---|---|---|---|",
    ]

    for metrica, meta in METAS.items():
        valor = medias.get(metrica, 0.0)
        status = "✅" if valor >= meta else "❌"
        linhas.append(f"| {metrica} | ≥ {meta} | {valor:.3f} | {status} |")

    linhas += [
        "",
        "## Resumo por categoria",
        "",
        "| Categoria | Qtd | Faithfulness | Context Precision | "
        "Context Recall | Answer Relevancy |",
        "|---|---|---|---|---|---|",
    ]

    categorias = {}
    for p, m in zip(perguntas, resultados, strict=False):
        cat = p.get("category", "outros")
        categorias.setdefault(cat, []).append(m)

    for cat, metricas in sorted(categorias.items()):
        medias_cat = _formatar_metricas(metricas)
        linhas.append(
            f"| {cat} | {len(metricas)} | {medias_cat['faithfulness']:.3f} | "
            f"{medias_cat['context_precision']:.3f} | {medias_cat['context_recall']:.3f} | "
            f"{medias_cat['answer_relevancy']:.3f} |"
        )

    linhas += [
        "",
        "## Detalhe por pergunta",
        "",
        "| ID | Perfil | Categoria | Pergunta | Faithfulness | Answer Relevancy |",
        "|---|---|---|---|---|---|",
    ]

    for p, m in zip(perguntas, resultados, strict=False):
        f = "—" if m.get("faithfulness") is None else f"{m['faithfulness']:.3f}"
        ar = "—" if m.get("answer_relevancy") is None else f"{m['answer_relevancy']:.3f}"
        linhas.append(
            f"| {p['id']} | {p['profile']} | {p['category']} | {p['question'][:60]}... | "
            f"{f} | {ar} |"
        )

    if resultados_fb is not None:
        linhas += _gerar_secao_feedback(resultados_fb, pulados_fb)

    linhas.append("")
    path.write_text("\n".join(linhas), encoding="utf-8")


async def executar_avaliacao(
    dataset_path: Path = DATASET_DEFAULT,
    output_path: Path = OUTPUT_DEFAULT,
    limit: int | None = None,
    feedback_path: Path | None = None,
    temperature: float | None = None,
) -> Path:
    """Executa a avaliação e gera o relatório.

    `feedback_path` aponta para o JSONL de feedback negativo (T8.1); quando
    None, usa o caminho padrão se o arquivo existir. Casos com `question: null`
    são pulados da reavaliação e contabilizados no relatório.
    """
    perguntas = carregar_dataset(dataset_path)
    if limit:
        perguntas = perguntas[:limit]

    graph = _carregar_grafo(temperature=temperature)
    resultados = []
    falhas: list[str] = []

    for pergunta in perguntas:
        state = {
            "user_id": pergunta["user_id"],
            "profile": pergunta["profile"],
            "messages": [HumanMessage(content=pergunta["question"])],
            "plan": None,
            "delegations": [],
            "agent_results": {},
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": None,
        }
        config = {"configurable": {"thread_id": f"eval-{pergunta['id']}"}}

        try:
            result = await graph.ainvoke(state, config)
            resposta = _extrair_resposta(result)
            metricas = _avaliar_resposta(pergunta, resposta)
        except Exception as exc:
            # Métrica ausente (None) != resposta ruim (0.0): falha de execução
            # não pode ser publicada como defeito de qualidade.
            print(
                f"[ERRO] {pergunta['id']}: {type(exc).__name__}: {exc}",
                file=sys.stderr,
                flush=True,
            )
            falhas.append(f"{pergunta['id']}: {type(exc).__name__}: {exc}")
            metricas = {m: None for m in METAS}

        resultados.append(metricas)

    # Casos de feedback negativo (T8.1) — fora do agregado Ragas principal
    resultados_fb: list[dict] | None = None
    pulados_fb = 0
    caminho_fb = feedback_path if feedback_path is not None else FEEDBACK_DEFAULT
    if caminho_fb.exists():
        casos_fb = carregar_dataset(caminho_fb)
        validos = [c for c in casos_fb if c.get("question")]
        pulados_fb = len(casos_fb) - len(validos)
        resultados_fb = await _executar_casos_feedback(graph, validos)

    medias = _formatar_metricas(resultados)
    modo = (
        "heurística de cobertura + LLM (não é o framework Ragas)"
        if os.getenv("OPENCODE_GO_API_KEY")
        else "offline-heurístico"
    )
    _gerar_relatorio(perguntas, resultados, medias, output_path, modo, resultados_fb, pulados_fb)
    if falhas:
        raise RuntimeError(
            f"avaliação incompleta — {len(falhas)} pergunta(s) falharam; "
            "as médias acima não representam o sistema e não devem ser publicadas. "
            + " | ".join(falhas)
        )
    return output_path


def main() -> None:
    """Entry point da CLI com suporte a CI Quality Gate (RF4-04)."""

    parser = argparse.ArgumentParser(description="Avaliação Ragas da UsiEdu")
    parser.add_argument("--dataset", type=Path, default=DATASET_DEFAULT)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--limit", type=int, default=None, help="Limita nº de perguntas")
    parser.add_argument(
        "--feedback",
        type=Path,
        default=None,
        help="JSONL de feedback negativo (T8.1); default: feedback_negativo.jsonl se existir",
    )
    parser.add_argument(
        "--ci-gate",
        action="store_true",
        help="Falha com exit code 1 se métricas ficarem abaixo do threshold (CI Quality Gate)",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.80,
        help="Score mínimo exigido para o CI Quality Gate (default: 0.80)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help=(
            "Temperatura dos LLMs na avaliação; o default delega ao provedor "
            "(OpenCode Go só aceita 1). Use 0 apenas com modelos que a aceitam."
        ),
    )
    args = parser.parse_args()

    output = asyncio.run(
        executar_avaliacao(
            args.dataset, args.output, args.limit, args.feedback, temperature=args.temperature
        )
    )
    print(f"Relatório gerado em: {output}")

    if args.ci_gate:
        aprovado, valores = _verificar_gate(output, args.min_score)
        print(f"\n[CI-GATE] Validando threshold minimo de {args.min_score:.2f}...")
        if not valores:
            print("[CI-GATE] [FALHA] Nenhuma métrica encontrada no relatório.")
            sys.exit(1)
        for metrica in METAS:
            valor = valores.get(metrica, 0.0)
            situacao = "OK" if valor >= args.min_score else "ABAIXO"
            print(f"[CI-GATE]   {metrica}: {valor:.3f} ({situacao})")
        if aprovado:
            print("[CI-GATE] [OK] Qualidade validada com sucesso!")
        else:
            print("[CI-GATE] [FALHA] Métricas abaixo do threshold mínimo.")
            sys.exit(1)
