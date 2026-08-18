"""Testes da API REST (auth + chat)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


class TestAuth:
    """Testes do endpoint de autenticação."""

    def test_autenticar_usuario_valido(self) -> None:
        """Login com credenciais válidas deve retornar token."""
        from src.api.auth import autenticar_usuario

        result = autenticar_usuario("ana@demo.usiedu", "estudante123")
        assert result is not None
        assert result.profile == "student"
        assert result.display_name == "Ana Souza"
        assert result.access_token is not None
        assert result.token_type == "bearer"

    def test_autenticar_usuario_invalido(self) -> None:
        """Login com senha errada deve retornar None."""
        from src.api.auth import autenticar_usuario

        result = autenticar_usuario("ana@demo.usiedu", "senha-errada")
        assert result is None

    def test_autenticar_email_inexistente(self) -> None:
        """Login com e-mail inexistente deve retornar None."""
        from src.api.auth import autenticar_usuario

        result = autenticar_usuario("nao-existe@demo.usiedu", "qualquer")
        assert result is None

    def test_login_endpoint_sucesso(self) -> None:
        """POST /auth/login com credenciais válidas deve retornar 200."""
        from src.api.main import app

        client = TestClient(app)
        response = client.post(
            "/auth/login",
            json={"email": "ana@demo.usiedu", "password": "estudante123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["profile"] == "student"
        assert "access_token" in data

    def test_login_endpoint_falha(self) -> None:
        """POST /auth/login com credenciais inválidas deve retornar 401."""
        from src.api.main import app

        client = TestClient(app)
        response = client.post(
            "/auth/login",
            json={"email": "ana@demo.usiedu", "password": "errada"},
        )
        assert response.status_code == 401

    def test_health_endpoint(self) -> None:
        """GET /health deve retornar status ok."""
        from src.api.main import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_ready_endpoint_requires_completed_startup(self) -> None:
        from src.api.main import create_app

        app = create_app()
        client = TestClient(app)

        assert client.get("/ready").status_code == 503

        app.state.ready = True
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}


class TestChatEndpoint:
    """Testes do endpoint de chat."""

    @pytest.mark.asyncio
    async def test_chat_sem_grafo_retorna_500(self) -> None:
        """Chat sem grafo inicializado deve retornar 500."""
        from src.api import chat as chat_module
        from src.api.main import app

        # Garante que o grafo está vazio
        chat_module._graph = None

        client = TestClient(app)
        token = _get_token(client)
        response = client.post(
            "/chat",
            json={"session_id": "sess-1", "message": "Quero ver minhas notas"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 500
        assert "não inicializado" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_chat_sem_token_retorna_401(self) -> None:
        """Chat sem token deve retornar 401."""
        from src.api.main import app

        client = TestClient(app)
        response = client.post(
            "/chat",
            json={"session_id": "sess-1", "message": "Quero ver minhas notas"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_com_grafo_fake(self) -> None:
        """Chat com grafo fake deve processar mensagem e retornar resposta."""
        from src.api import chat as chat_module
        from src.api.main import app
        from src.llm.fake import FakeChatModel
        from src.orchestration.graph import create_chat_graph

        # Cria grafo com LLMs fake
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
        graph = create_chat_graph(router_llm=router_llm, agent_llm=agent_llm)

        # Injeta no módulo de chat
        chat_module._graph = graph

        client = TestClient(app)
        token = _get_token(client)
        response = client.post(
            "/chat",
            json={"session_id": "sess-2", "message": "Quero ver minhas notas"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "sess-2"
        assert data["intent"] == "academico"
        assert "academico" in data["agents_involved"]
        assert len(data["answer"]) > 0


def _get_token(client: TestClient) -> str:
    """Obtém token JWT para usuário demo."""
    response = client.post(
        "/auth/login",
        json={"email": "ana@demo.usiedu", "password": "estudante123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]
