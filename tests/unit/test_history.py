"""Testes do endpoint de histórico de chat (T7.4 — RF2-04, RF2-05)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient


def _get_token(
    client: TestClient, email: str = "ana@demo.usiedu", password: str = "estudante123"
) -> str:
    """Obtém token JWT para usuário demo."""
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _make_fake_graph():
    """Cria grafo com LLMs fake e MemorySaver (checkpointer em memória)."""
    from src.llm.fake import FakeChatModel
    from src.orchestration.graph import create_chat_graph

    router_llm = FakeChatModel(
        default_response=json.dumps(
            {
                "intent": "academico",
                "plan": None,
                "reasoning": "teste",
            }
        )
    )
    agent_llm = FakeChatModel(default_response="Resposta fake do agente.")
    return create_chat_graph(router_llm=router_llm, agent_llm=agent_llm)


class TestChatHistory:
    """Testes do endpoint GET /chat/history."""

    def test_history_sem_token_retorna_401(self) -> None:
        """Histórico sem token deve retornar 401."""
        from src.api.main import app

        client = TestClient(app)
        response = client.get("/chat/history", params={"session_id": "sess-x"})
        assert response.status_code == 401

    def test_history_sem_grafo_retorna_500(self) -> None:
        """Histórico sem grafo inicializado deve retornar 500."""
        from src.api import chat as chat_module
        from src.api.main import app

        chat_module._graph = None

        client = TestClient(app)
        token = _get_token(client)
        response = client.get(
            "/chat/history",
            params={"session_id": "sess-x"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 500
        assert "não inicializado" in response.json()["detail"]

    def test_history_sessao_inexistente_retorna_404(self) -> None:
        """Histórico de sessão desconhecida deve retornar 404."""
        from src.api import chat as chat_module
        from src.api.main import app

        chat_module._graph = _make_fake_graph()

        client = TestClient(app)
        token = _get_token(client)
        response = client.get(
            "/chat/history",
            params={"session_id": "sess-inexistente"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "Sessão não encontrada" in response.json()["detail"]

    def test_history_proprio_retorna_mensagens_na_ordem(self) -> None:
        """Após conversar, o dono da sessão recebe as mensagens na ordem."""
        from src.api import chat as chat_module
        from src.api.main import app

        chat_module._graph = _make_fake_graph()

        client = TestClient(app)
        token = _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        chat_response = client.post(
            "/chat",
            json={"session_id": "sess-hist-1", "message": "Quero ver minhas notas"},
            headers=headers,
        )
        assert chat_response.status_code == 200

        response = client.get(
            "/chat/history",
            params={"session_id": "sess-hist-1"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "sess-hist-1"
        messages = data["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Quero ver minhas notas"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Resposta fake do agente."

    def test_history_de_outro_usuario_retorna_403(self) -> None:
        """Sessão criada por um usuário não pode ser lida por outro."""
        from src.api import chat as chat_module
        from src.api.main import app

        chat_module._graph = _make_fake_graph()

        client = TestClient(app)
        token_ana = _get_token(client)
        token_carlos = _get_token(client, email="carlos@demo.usiedu", password="staff123")

        chat_response = client.post(
            "/chat",
            json={"session_id": "sess-hist-2", "message": "Quero ver minhas notas"},
            headers={"Authorization": f"Bearer {token_ana}"},
        )
        assert chat_response.status_code == 200

        response = client.get(
            "/chat/history",
            params={"session_id": "sess-hist-2"},
            headers={"Authorization": f"Bearer {token_carlos}"},
        )
        assert response.status_code == 403
        assert "outro usuário" in response.json()["detail"]
