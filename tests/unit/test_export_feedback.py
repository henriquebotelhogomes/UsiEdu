"""Testes da exportação de feedback negativo para o dataset de avaliação (T8.1)."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph

from scripts.export_feedback_to_eval import (
    carregar_exportados,
    carregar_feedbacks_negativos,
    exportar,
)
from src.orchestration.state import AgentState

_SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    rating TEXT NOT NULL CHECK (rating IN ('up', 'down')),
    comment TEXT,
    user_email TEXT NOT NULL,
    profile TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


def _criar_db_feedback(path: Path, linhas: list[tuple]) -> None:
    con = sqlite3.connect(path)
    con.execute(_SCHEMA)
    con.executemany(
        """
        INSERT INTO feedback
            (session_id, message_id, rating, comment, user_email, profile, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        linhas,
    )
    con.commit()
    con.close()


class TestCarregarFeedbacks:
    def test_filtra_apenas_rating_down(self, tmp_path) -> None:
        db = tmp_path / "feedback.db"
        _criar_db_feedback(
            db,
            [
                ("s1", "m1", "up", None, "ana@demo.usiedu", "student", "2026-08-01T10:00:00"),
                (
                    "s1",
                    "m2",
                    "down",
                    "resposta incompleta",
                    "ana@demo.usiedu",
                    "student",
                    "2026-08-01T10:05:00",
                ),
                ("s2", "m3", "down", None, "carlos@demo.usiedu", "staff", "2026-08-01T11:00:00"),
            ],
        )
        feedbacks = asyncio.run(carregar_feedbacks_negativos(str(db)))
        assert len(feedbacks) == 2
        assert {f["message_id"] for f in feedbacks} == {"m2", "m3"}
        assert feedbacks[0]["user_comment"] == "resposta incompleta"

    def test_banco_inexistente_retorna_vazio(self, tmp_path) -> None:
        feedbacks = asyncio.run(carregar_feedbacks_negativos(str(tmp_path / "nao_existe.db")))
        assert feedbacks == []


class TestExportar:
    def test_jsonl_valido_e_campos(self, tmp_path) -> None:
        db = tmp_path / "feedback.db"
        _criar_db_feedback(
            db,
            [("s1", "m1", "down", "errado", "ana@demo.usiedu", "student", "2026-08-01T10:00:00")],
        )
        out = tmp_path / "feedback_negativo.jsonl"

        resumo = asyncio.run(exportar(str(db), out, checkpointer_db=str(tmp_path / "sem_ckpt.db")))
        assert resumo["novos"] == 1
        assert resumo["sem_pergunta"] == 1  # sem checkpointer → question null

        linhas = out.read_text(encoding="utf-8").strip().splitlines()
        caso = json.loads(linhas[0])
        assert caso["question"] is None
        assert caso["rejected_answer"] is None
        assert caso["user_comment"] == "errado"
        assert caso["profile"] == "student"
        assert caso["session_id"] == "s1"
        assert caso["message_id"] == "m1"
        assert caso["created_at"] == "2026-08-01T10:00:00"

    def test_idempotencia_nao_duplica(self, tmp_path) -> None:
        db = tmp_path / "feedback.db"
        _criar_db_feedback(
            db,
            [
                ("s1", "m1", "down", None, "ana@demo.usiedu", "student", "2026-08-01T10:00:00"),
                ("s1", "m2", "down", None, "ana@demo.usiedu", "student", "2026-08-01T10:05:00"),
            ],
        )
        out = tmp_path / "feedback_negativo.jsonl"

        primeiro = asyncio.run(
            exportar(str(db), out, checkpointer_db=str(tmp_path / "sem_ckpt.db"))
        )
        segundo = asyncio.run(exportar(str(db), out, checkpointer_db=str(tmp_path / "sem_ckpt.db")))

        assert primeiro["novos"] == 2
        assert segundo["novos"] == 0
        assert segundo["pulados_ja_exportados"] == 2
        assert len(carregar_exportados(out)) == 2

    def test_dry_run_nao_escreve(self, tmp_path) -> None:
        db = tmp_path / "feedback.db"
        _criar_db_feedback(
            db,
            [("s1", "m1", "down", None, "ana@demo.usiedu", "student", "2026-08-01T10:00:00")],
        )
        out = tmp_path / "feedback_negativo.jsonl"

        resumo = asyncio.run(
            exportar(str(db), out, checkpointer_db=str(tmp_path / "sem.db"), dry_run=True)
        )
        assert resumo["novos"] == 1
        assert not out.exists()

    @pytest.mark.asyncio
    async def test_pergunta_recuperada_do_checkpointer(self, tmp_path) -> None:
        """Com checkpointer, pergunta e resposta rejeitada devem ser recuperadas."""
        ckpt = tmp_path / "ckpt.db"

        # Grafo mínimo que ecoa uma resposta (grava checkpoint com metadados)
        def responde(state: AgentState) -> dict:
            return {"messages": [AIMessage(content="Resposta rejeitada pelo usuário.")]}

        builder = StateGraph(AgentState)
        builder.add_node("responde", responde)
        builder.set_entry_point("responde")
        builder.set_finish_point("responde")

        async with AsyncSqliteSaver.from_conn_string(str(ckpt)) as saver:
            graph = builder.compile(checkpointer=saver)
            await graph.ainvoke(
                {"messages": [HumanMessage(content="Quando começa o semestre?")]},
                {
                    "configurable": {"thread_id": "sessao-x"},
                    "metadata": {"message_id": "abc-123"},
                },
            )

        db = tmp_path / "feedback.db"
        _criar_db_feedback(
            db,
            [
                (
                    "sessao-x",
                    "abc-123",
                    "down",
                    "não respondeu a data",
                    "ana@demo.usiedu",
                    "student",
                    "2026-08-01T10:00:00",
                )
            ],
        )
        out = tmp_path / "feedback_negativo.jsonl"

        resumo = await exportar(str(db), out, checkpointer_db=str(ckpt))
        assert resumo["novos"] == 1
        assert resumo["sem_pergunta"] == 0

        caso = carregar_exportados(out)[0]
        assert caso["question"] == "Quando começa o semestre?"
        assert caso["rejected_answer"] == "Resposta rejeitada pelo usuário."

    @pytest.mark.asyncio
    async def test_sessao_inexistente_question_null(self, tmp_path) -> None:
        """Feedback apontando para sessão sem checkpoints exporta question: null."""
        ckpt = tmp_path / "ckpt_vazio.db"
        async with AsyncSqliteSaver.from_conn_string(str(ckpt)):
            pass  # apenas cria o banco vazio

        db = tmp_path / "feedback.db"
        _criar_db_feedback(
            db,
            [
                (
                    "sessao-fantasma",
                    "m1",
                    "down",
                    None,
                    "ana@demo.usiedu",
                    "student",
                    "2026-08-01T10:00:00",
                )
            ],
        )
        out = tmp_path / "feedback_negativo.jsonl"

        resumo = await exportar(str(db), out, checkpointer_db=str(ckpt))
        assert resumo["novos"] == 1
        assert resumo["sem_pergunta"] == 1
        assert carregar_exportados(out)[0]["question"] is None


class TestMain:
    def test_cli_executa(self, tmp_path, monkeypatch, capsys) -> None:
        from scripts.export_feedback_to_eval import main

        db = tmp_path / "feedback.db"
        _criar_db_feedback(
            db,
            [("s1", "m1", "down", None, "ana@demo.usiedu", "student", "2026-08-01T10:00:00")],
        )
        out = tmp_path / "out.jsonl"
        monkeypatch.setattr(
            "sys.argv",
            [
                "export_feedback_to_eval",
                "--db",
                str(db),
                "--out",
                str(out),
                "--checkpointer-db",
                str(tmp_path / "sem.db"),
            ],
        )
        main()
        assert out.exists()
        assert "1 caso(s) novo(s)" in capsys.readouterr().out
