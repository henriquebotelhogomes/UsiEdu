"""Exporta feedbacks negativos (👎) para o dataset de regressão da avaliação (T8.1).

Lê o banco SQLite de feedback (`USIEDU_FEEDBACK_DB`), recupera a pergunta
original e a resposta rejeitada no checkpointer da sessão (metadados do
checkpoint guardam o `message_id` da execução) e anexa os casos a
`src/evaluation/feedback_negativo.jsonl`.

Idempotência: a chave de deduplicação é o `message_id` — reexecutar o script
não duplica registros. Casos sem pergunta recuperável são exportados com
`question: null` e pulados na etapa Ragas.

Uso:
    python scripts/export_feedback_to_eval.py [--db PATH] [--out PATH]
                                              [--checkpointer-db PATH] [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aiosqlite
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph

from src.orchestration.state import AgentState

FEEDBACK_DB_DEFAULT = os.getenv("USIEDU_FEEDBACK_DB", "usiedu_feedback.db")
CHECKPOINTER_DB_DEFAULT = os.getenv("USIEDU_CHECKPOINTER_DB", "usiedu_checkpoints.db")
OUT_DEFAULT = Path(__file__).parent.parent / "src" / "evaluation" / "feedback_negativo.jsonl"


def carregar_exportados(out_path: Path) -> list[dict]:
    """Carrega os casos já exportados no JSONL (arquivo ausente → lista vazia)."""
    if not out_path.exists():
        return []
    casos = []
    with out_path.open(encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                casos.append(json.loads(linha))
    return casos


async def carregar_feedbacks_negativos(db_path: str) -> list[dict]:
    """Lê todos os feedbacks 👎 do banco SQLite (banco ausente → lista vazia)."""
    if not Path(db_path).exists():
        return []
    async with aiosqlite.connect(db_path) as db:
        try:
            async with db.execute(
                """
                SELECT session_id, message_id, rating, comment, profile, created_at
                FROM feedback
                WHERE rating = 'down'
                ORDER BY created_at ASC
                """
            ) as cursor:
                rows = await cursor.fetchall()
        except aiosqlite.OperationalError:
            return []  # tabela ainda não criada (nenhum feedback registrado)
    return [
        {
            "session_id": row[0],
            "message_id": row[1],
            "rating": row[2],
            "user_comment": row[3],
            "profile": row[4],
            "created_at": row[5],
        }
        for row in rows
    ]


def _grafo_leitura(checkpointer: AsyncSqliteSaver):
    """Grafo mínimo apenas para leitura de estado via checkpointer.

    Nenhum nó real é executado: o grafo serve somente como interface do
    LangGraph para desserializar os checkpoints da thread.
    """
    builder = StateGraph(AgentState)
    builder.add_node("noop", lambda state: {})
    builder.set_entry_point("noop")
    builder.set_finish_point("noop")
    return builder.compile(checkpointer=checkpointer)


async def recuperar_turno(graph, session_id: str, message_id: str) -> tuple[str | None, str | None]:
    """Recupera (pergunta, resposta rejeitada) do turno apontado por message_id.

    Percorre o histórico de checkpoints da sessão (do mais recente para o mais
    antigo); o primeiro snapshot cujos metadados trazem o `message_id` é o
    estado final daquela execução: a última HumanMessage é a pergunta e a
    última AIMessage é a resposta que recebeu o 👎.
    """
    try:
        config = {"configurable": {"thread_id": session_id}}
        async for snap in graph.aget_state_history(config):
            if (snap.metadata or {}).get("message_id") != message_id:
                continue
            messages = snap.values.get("messages") or []
            pergunta = next(
                (
                    m.content
                    for m in reversed(messages)
                    if isinstance(m, HumanMessage) and isinstance(m.content, str)
                ),
                None,
            )
            resposta = next(
                (
                    m.content
                    for m in reversed(messages)
                    if isinstance(m, AIMessage) and isinstance(m.content, str)
                ),
                None,
            )
            return pergunta, resposta
    except Exception:  # noqa: BLE001 — checkpoint indisponível não bloqueia a exportação
        pass
    return None, None


async def exportar(
    db_path: str = FEEDBACK_DB_DEFAULT,
    out_path: Path = OUT_DEFAULT,
    checkpointer_db: str = CHECKPOINTER_DB_DEFAULT,
    dry_run: bool = False,
) -> dict:
    """Exporta os 👎 novos para o JSONL. Retorna resumo da operação."""
    feedbacks = await carregar_feedbacks_negativos(db_path)
    ja_exportados = {c["message_id"] for c in carregar_exportados(out_path)}

    # Deduplicação por message_id (último comentário registrado vence)
    novos: dict[str, dict] = {}
    for fb in feedbacks:
        if fb["message_id"] in ja_exportados:
            continue
        novos[fb["message_id"]] = fb

    casos: list[dict] = []
    sem_pergunta = 0
    if novos:
        if Path(checkpointer_db).exists():
            async with AsyncSqliteSaver.from_conn_string(checkpointer_db) as saver:
                graph = _grafo_leitura(saver)
                for fb in novos.values():
                    pergunta, rejeitada = await recuperar_turno(
                        graph, fb["session_id"], fb["message_id"]
                    )
                    if pergunta is None:
                        sem_pergunta += 1
                    casos.append(
                        {
                            "question": pergunta,
                            "rejected_answer": rejeitada,
                            "user_comment": fb["user_comment"],
                            "profile": fb["profile"],
                            "session_id": fb["session_id"],
                            "message_id": fb["message_id"],
                            "created_at": fb["created_at"],
                        }
                    )
        else:
            # Sem checkpointer: exporta com question null (pulado na etapa Ragas)
            for fb in novos.values():
                sem_pergunta += 1
                casos.append(
                    {
                        "question": None,
                        "rejected_answer": None,
                        "user_comment": fb["user_comment"],
                        "profile": fb["profile"],
                        "session_id": fb["session_id"],
                        "message_id": fb["message_id"],
                        "created_at": fb["created_at"],
                    }
                )

    if casos and not dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("a", encoding="utf-8") as f:
            for caso in casos:
                f.write(json.dumps(caso, ensure_ascii=False) + "\n")

    return {
        "novos": len(casos),
        "pulados_ja_exportados": len(feedbacks) - len(novos),
        "sem_pergunta": sem_pergunta,
        "out": str(out_path),
        "dry_run": dry_run,
    }


def main() -> None:
    """Entry point da CLI."""
    parser = argparse.ArgumentParser(
        description="Exporta feedbacks 👎 para o dataset de regressão (T8.1)"
    )
    parser.add_argument("--db", default=FEEDBACK_DB_DEFAULT, help="Banco SQLite de feedback")
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT, help="JSONL de destino")
    parser.add_argument(
        "--checkpointer-db",
        default=CHECKPOINTER_DB_DEFAULT,
        help="Banco SQLite do checkpointer (pergunta original)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simula a exportação sem escrever o JSONL"
    )
    args = parser.parse_args()

    resumo = asyncio.run(exportar(args.db, args.out, args.checkpointer_db, args.dry_run))

    prefixo = "[dry-run] " if resumo["dry_run"] else ""
    print(
        f"{prefixo}{resumo['novos']} caso(s) novo(s) exportado(s), "
        f"{resumo['pulados_ja_exportados']} já presente(s), "
        f"{resumo['sem_pergunta']} sem pergunta recuperada → {resumo['out']}"
    )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
