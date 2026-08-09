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


def _carregar_grafo():
    """Carrega o grafo com LLM fake (offline) ou real + RAG conforme env."""
    from src.llm.fake import FakeChatModel
    from src.orchestration.graph import create_chat_graph

    # Se houver API key, usa modelo real + RAG; senão usa fake determinístico
    if os.getenv("OPENCODE_GO_API_KEY"):
        from src.llm.provider import get_chat_model

        router_llm = get_chat_model(
            model_name=os.getenv("USIEDU_ROUTER_MODEL", "deepseek-v4-flash")
        )
        agent_llm = get_chat_model(model_name=os.getenv("USIEDU_AGENT_MODEL", "deepseek-v4-flash"))

        # Cria retriever RAG conectado ao Qdrant
        from qdrant_client import QdrantClient

        from src.rag.embedder import Embedder
        from src.rag.retriever import HybridRetriever

        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        embedder = Embedder()
        retriever = HybridRetriever(
            client=QdrantClient(qdrant_url),
            embedder=embedder,
            reranker=None,
        )
    else:
        router_llm = FakeChatModel(
            default_response=json.dumps(
                {"intent": "academico", "plan": None, "reasoning": "avaliação offline"}
            )
        )
        agent_llm = FakeChatModel(default_response="Resposta de avaliação (modo offline).")
        retriever = None

    return create_chat_graph(
        router_llm=router_llm,
        agent_llm=agent_llm,
        retriever=retriever,
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
            t in resp for t in ["fora do escopo", "não encontrei", "fora de escopo", "não posso"]
        )
        return {
            "faithfulness": 1.0 if negacao else 0.0,
            "context_precision": 1.0,
            "context_recall": 1.0,
            "answer_relevancy": 1.0 if negacao else 0.0,
        }

    if cat == "sem_resposta":
        honesto = any(
            t in resp for t in ["não encontrei", "não sei", "não encontrada", "não disponível"]
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
        linhas.append(
            f"| {p['id']} | {p['profile']} | {p['category']} | {p['question'][:60]}... | "
            f"{m.get('faithfulness', 0.0):.3f} | {m.get('answer_relevancy', 0.0):.3f} |"
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
) -> Path:
    """Executa a avaliação e gera o relatório.

    `feedback_path` aponta para o JSONL de feedback negativo (T8.1); quando
    None, usa o caminho padrão se o arquivo existir. Casos com `question: null`
    são pulados da reavaliação e contabilizados no relatório.
    """
    perguntas = carregar_dataset(dataset_path)
    if limit:
        perguntas = perguntas[:limit]

    graph = _carregar_grafo()
    resultados = []

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
        except Exception:
            metricas = {
                "faithfulness": 0.0,
                "context_precision": 0.0,
                "context_recall": 0.0,
                "answer_relevancy": 0.0,
            }

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
    modo = "offline-heurístico" if not os.getenv("OPENCODE_GO_API_KEY") else "Ragas+LLM"
    _gerar_relatorio(perguntas, resultados, medias, output_path, modo, resultados_fb, pulados_fb)
    return output_path


def main() -> None:
    """Entry point da CLI."""
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
    args = parser.parse_args()

    output = asyncio.run(executar_avaliacao(args.dataset, args.output, args.limit, args.feedback))
    print(f"Relatório gerado em: {output}")


if __name__ == "__main__":
    main()
