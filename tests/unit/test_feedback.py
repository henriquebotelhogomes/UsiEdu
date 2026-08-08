"""Testes do endpoint de feedback humano (human-on-the-loop)."""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    """Client da API com banco de feedback isolado em tmp."""
    monkeypatch.setenv("USIEDU_FEEDBACK_DB", str(tmp_path / "feedback.db"))
    from src.api.main import app

    return TestClient(app)


def _get_token(client: TestClient) -> str:
    response = client.post(
        "/auth/login",
        json={"email": "ana@demo.usiedu", "password": "estudante123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


class TestFeedback:
    """Testes do POST /feedback e GET /feedback/stats."""

    def test_feedback_sem_token_retorna_401(self, client: TestClient) -> None:
        """Feedback sem autenticação deve retornar 401."""
        response = client.post(
            "/feedback",
            json={"session_id": "s1", "message_id": str(uuid.uuid4()), "rating": "up"},
        )
        assert response.status_code == 401

    def test_feedback_valido_retorna_200(self, client: TestClient) -> None:
        """Feedback válido deve ser registrado e retornar id."""
        token = _get_token(client)
        response = client.post(
            "/feedback",
            json={"session_id": "s1", "message_id": str(uuid.uuid4()), "rating": "up"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert isinstance(data["feedback_id"], int)

    def test_feedback_rating_invalido_retorna_422(self, client: TestClient) -> None:
        """Rating fora de up/down deve retornar 422."""
        token = _get_token(client)
        response = client.post(
            "/feedback",
            json={"session_id": "s1", "message_id": str(uuid.uuid4()), "rating": "lado"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_stats_reflete_feedbacks(self, client: TestClient) -> None:
        """Stats deve agregar up/down e calcular satisfação."""
        token = _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        for rating in ("up", "up", "down"):
            r = client.post(
                "/feedback",
                json={"session_id": "s1", "message_id": str(uuid.uuid4()), "rating": rating},
                headers=headers,
            )
            assert r.status_code == 200

        stats = client.get("/feedback/stats", headers=headers)
        assert stats.status_code == 200
        data = stats.json()
        assert data["total"] == 3
        assert data["up"] == 2
        assert data["down"] == 1
        assert data["satisfaction"] == pytest.approx(2 / 3, abs=1e-3)

    def test_stats_sem_token_retorna_401(self, client: TestClient) -> None:
        """Stats sem autenticação deve retornar 401."""
        assert client.get("/feedback/stats").status_code == 401


class TestChatMessageId:
    """O /chat deve retornar message_id para viabilizar o feedback."""

    def test_chat_retorna_message_id(self, client: TestClient) -> None:
        """Resposta do chat deve incluir message_id (run_id do trace)."""
        from src.api import chat as chat_module
        from src.llm.fake import FakeChatModel
        from src.orchestration.graph import create_chat_graph

        router_llm = FakeChatModel(
            default_response=json.dumps({"intent": "academico", "plan": None, "reasoning": "teste"})
        )
        agent_llm = FakeChatModel(default_response="Resposta fake.")
        chat_module._graph = create_chat_graph(router_llm=router_llm, agent_llm=agent_llm)

        token = _get_token(client)
        response = client.post(
            "/chat",
            json={"session_id": "sess-fb", "message": "Quero ver minhas notas"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        message_id = response.json()["message_id"]
        uuid.UUID(message_id)  # deve ser um UUID válido

        # Feedback aceita esse message_id
        fb = client.post(
            "/feedback",
            json={"session_id": "sess-fb", "message_id": message_id, "rating": "up"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fb.status_code == 200

        chat_module._graph = None
