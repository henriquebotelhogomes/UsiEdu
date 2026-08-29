"""Testes de Human-in-the-Loop (HITL) e Retomada de Fluxo (RF4-01, RF4-02)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from src.llm.fake import FakeChatModel
from src.orchestration.graph import create_chat_graph


def _get_token(client: TestClient) -> str:
    response = client.post(
        "/auth/login",
        json={"email": "ana@demo.usiedu", "password": "estudante123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _make_hitl_graph(interrupt_before: list[str] | None = None):
    router_llm = FakeChatModel(
        default_response=json.dumps(
            {"intent": "financeiro", "plan": None, "reasoning": "teste hitl"}
        )
    )
    agent_llm = FakeChatModel(default_response="Simulação financeira concluída.")
    return create_chat_graph(
        router_llm=router_llm,
        agent_llm=agent_llm,
        checkpointer=MemorySaver(),
        interrupt_before=interrupt_before or ["consolidation"],
    )


class TestHumanInTheLoop:
    """Testes de interrupção e retomada de fluxo no grafo."""

    @pytest.mark.asyncio
    async def test_grafo_pausa_no_interrupt_before(self) -> None:
        """Grafo com interrupt_before deve pausar a execução antes do nó configurado."""
        graph = _make_hitl_graph(interrupt_before=["consolidation"])
        config = {"configurable": {"thread_id": "thread-hitl-1"}}

        state = {
            "user_id": "ana@demo.usiedu",
            "profile": "student",
            "messages": [],
            "plan": None,
            "delegations": [],
            "agent_results": {},
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": None,
        }

        # Primeira invocação: deve executar até o interrupt_before
        await graph.ainvoke(state, config)

        snapshot = await graph.aget_state(config)
        assert snapshot.next == ("consolidation",)

    def test_endpoint_resume_retoma_execucao(self) -> None:
        """Endpoint /chat/resume deve retomar e finalizar o fluxo pausado."""
        from src.api import chat as chat_module
        from src.api.main import app

        graph = _make_hitl_graph(interrupt_before=["consolidation"])
        chat_module.init_graph(graph)

        client = TestClient(app)
        token = _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Inicia conversa (pausa antes da consolidação)
        chat_res = client.post(
            "/chat",
            json={"session_id": "sess-hitl-2", "message": "Quero renegociar minha dívida"},
            headers=headers,
        )
        assert chat_res.status_code == 200

        # 2. Retoma execução via /chat/resume
        resume_res = client.post(
            "/chat/resume",
            json={
                "session_id": "sess-hitl-2",
                "approved": True,
                "user_input": "Confirmo o parcelamento em 3x",
            },
            headers=headers,
        )
        assert resume_res.status_code == 200
        data = resume_res.json()
        assert data["session_id"] == "sess-hitl-2"
        assert data["answer"]

    @pytest.mark.asyncio
    async def test_grafo_com_sqlite_checkpointer_persiste_estado(
        self, tmp_path, monkeypatch
    ) -> None:
        """Grafo criado com USIEDU_CHECKPOINTER_DB deve persistir estado no SQLite."""
        db_file = tmp_path / "checkpoints_test.db"
        monkeypatch.setenv("USIEDU_CHECKPOINTER_DB", str(db_file))

        router_llm = FakeChatModel(
            default_response=json.dumps(
                {"intent": "academico", "plan": None, "reasoning": "teste sqlite"}
            )
        )
        agent_llm = FakeChatModel(default_response="Resposta persistida.")
        graph = create_chat_graph(
            router_llm=router_llm,
            agent_llm=agent_llm,
            checkpointer=None,  # Deve instanciar SqliteSaver automaticamente
            interrupt_before=["consolidation"],
        )

        config = {"configurable": {"thread_id": "thread-sqlite-1"}}
        state = {
            "user_id": "aluno@teste.com",
            "profile": "student",
            "messages": [],
            "plan": None,
            "delegations": [],
            "agent_results": {},
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": None,
        }

        await graph.ainvoke(state, config)
        assert db_file.exists()
        assert db_file.stat().st_size > 0

        snapshot = await graph.aget_state(config)
        assert snapshot.next == ("consolidation",)

        # Fecha conexão do checkpointer de forma limpa
        if hasattr(graph.checkpointer, "conn"):
            await graph.checkpointer.conn.close()

