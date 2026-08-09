"""Testes de rate limiting das rotas da API (T9.1).

Cobrem os critérios de aceite: estourar o limite retorna 429 (com corpo
``{detail}`` e header ``Retry-After``); após a janela expirar (simulada via
``limiter.reset()``) volta a 200; e as chaves são independentes por usuário
(chat) e por IP (login).
"""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient

CREDENCIAIS_ANA = {"email": "ana@demo.usiedu", "password": "estudante123"}
CREDENCIAIS_CARLOS = {"email": "carlos@demo.usiedu", "password": "staff123"}


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    """Client da API com banco de feedback isolado e LangSmith desligado."""
    monkeypatch.setenv("USIEDU_FEEDBACK_DB", str(tmp_path / "feedback.db"))

    import src.api.feedback as feedback_module

    # Evita 30+ chamadas de rede ao LangSmith nos testes de estouro
    monkeypatch.setattr(feedback_module, "_envia_feedback_langsmith", lambda *args: None)

    from src.api.main import app

    return TestClient(app)


def _get_token(client: TestClient, credenciais: dict) -> str:
    response = client.post("/auth/login", json=credenciais)
    assert response.status_code == 200
    return response.json()["access_token"]


def _make_fake_graph():
    """Cria grafo com LLMs fake (mesmo padrão de test_chat_stream)."""
    from src.llm.fake import FakeChatModel
    from src.orchestration.graph import create_chat_graph

    router_llm = FakeChatModel(
        default_response=json.dumps({"intent": "academico", "plan": None, "reasoning": "teste"})
    )
    agent_llm = FakeChatModel(default_response="Resposta fake do agente.")
    return create_chat_graph(router_llm=router_llm, agent_llm=agent_llm)


class TestRateLimitLogin:
    """POST /auth/login — 5/min por IP."""

    def test_sexta_tentativa_retorna_429_com_retry_after(self, client: TestClient) -> None:
        """6ª tentativa de login no mesmo minuto → 429 com {detail} e Retry-After."""
        for _ in range(5):
            response = client.post(
                "/auth/login", json={"email": "ana@demo.usiedu", "password": "errada"}
            )
            assert response.status_code == 401

        response = client.post(
            "/auth/login", json={"email": "ana@demo.usiedu", "password": "errada"}
        )
        assert response.status_code == 429
        assert "detail" in response.json()
        assert "Retry-After" in response.headers

    def test_volta_200_apos_janela(self, client: TestClient) -> None:
        """Após a janela expirar (simulada via reset), login volta a funcionar."""
        from src.api.rate_limit import limiter

        for _ in range(5):
            client.post("/auth/login", json={"email": "ana@demo.usiedu", "password": "errada"})
        assert (
            client.post(
                "/auth/login", json={"email": "ana@demo.usiedu", "password": "errada"}
            ).status_code
            == 429
        )

        limiter.reset()  # simula o fim da janela de 1 minuto

        response = client.post("/auth/login", json=CREDENCIAIS_ANA)
        assert response.status_code == 200

    def test_ips_distintos_têm_contadores_separados(self, client: TestClient) -> None:
        """Chave por IP: estourar em um IP não afeta outro (X-Forwarded-For)."""
        payload = {"email": "ana@demo.usiedu", "password": "errada"}
        for _ in range(6):
            client.post("/auth/login", json=payload, headers={"X-Forwarded-For": "10.0.0.1"})
        assert (
            client.post(
                "/auth/login", json=payload, headers={"X-Forwarded-For": "10.0.0.1"}
            ).status_code
            == 429
        )

        # Outro IP segue com contador próprio (401 pela senha, não 429)
        assert (
            client.post(
                "/auth/login", json=payload, headers={"X-Forwarded-For": "10.0.0.2"}
            ).status_code
            == 401
        )


class TestRateLimitChat:
    """POST /chat e /chat/stream — 10/min por usuário autenticado."""

    def test_decima_primeira_pergunta_retorna_429(self, client: TestClient) -> None:
        """Critério de aceite: 11ª pergunta em 1 minuto → 429 com Retry-After."""
        from src.api import chat as chat_module

        chat_module._graph = _make_fake_graph()
        try:
            token = _get_token(client, CREDENCIAIS_ANA)
            headers = {"Authorization": f"Bearer {token}"}

            for i in range(10):
                response = client.post(
                    "/chat",
                    json={"session_id": f"sess-rl-{i}", "message": "Quero ver minhas notas"},
                    headers=headers,
                )
                assert response.status_code == 200

            response = client.post(
                "/chat",
                json={"session_id": "sess-rl-11", "message": "Quero ver minhas notas"},
                headers=headers,
            )
            assert response.status_code == 429
            assert "detail" in response.json()
            assert "Retry-After" in response.headers
        finally:
            chat_module._graph = None

    def test_volta_200_apos_janela(self, client: TestClient) -> None:
        """Após a janela expirar (simulada via reset), o chat volta a responder."""
        from src.api import chat as chat_module
        from src.api.rate_limit import limiter

        chat_module._graph = _make_fake_graph()
        try:
            token = _get_token(client, CREDENCIAIS_ANA)
            headers = {"Authorization": f"Bearer {token}"}
            body = {"session_id": "sess-rl-reset", "message": "Quero ver minhas notas"}

            for _ in range(10):
                client.post("/chat", json=body, headers=headers)
            assert client.post("/chat", json=body, headers=headers).status_code == 429

            limiter.reset()  # simula o fim da janela de 1 minuto

            assert client.post("/chat", json=body, headers=headers).status_code == 200
        finally:
            chat_module._graph = None

    def test_usuarios_distintos_têm_limites_independentes(self, client: TestClient) -> None:
        """Chave por e-mail JWT: estourar o limite da Ana não afeta o Carlos."""
        from src.api import chat as chat_module

        chat_module._graph = _make_fake_graph()
        try:
            headers_ana = {"Authorization": f"Bearer {_get_token(client, CREDENCIAIS_ANA)}"}
            headers_carlos = {"Authorization": f"Bearer {_get_token(client, CREDENCIAIS_CARLOS)}"}
            body = {"session_id": "sess-rl-chave", "message": "Quero ver minhas notas"}

            for _ in range(10):
                client.post("/chat", json=body, headers=headers_ana)
            assert client.post("/chat", json=body, headers=headers_ana).status_code == 429

            # Carlos tem contador próprio: segue com 200
            assert client.post("/chat", json=body, headers=headers_carlos).status_code == 200
        finally:
            chat_module._graph = None

    def test_stream_tambem_tem_limite(self, client: TestClient) -> None:
        """/chat/stream tem o mesmo limite de 10/min por usuário."""
        from src.api import chat as chat_module

        chat_module._graph = _make_fake_graph()
        try:
            token = _get_token(client, CREDENCIAIS_ANA)
            headers = {"Authorization": f"Bearer {token}"}
            body = {"session_id": "sess-rl-stream", "message": "Quero ver minhas notas"}

            for _ in range(10):
                assert client.post("/chat/stream", json=body, headers=headers).status_code == 200

            assert client.post("/chat/stream", json=body, headers=headers).status_code == 429
        finally:
            chat_module._graph = None


class TestRateLimitFeedback:
    """POST /feedback — 30/min por usuário autenticado."""

    def test_trigesimo_primeiro_feedback_retorna_429(self, client: TestClient) -> None:
        token = _get_token(client, CREDENCIAIS_ANA)
        headers = {"Authorization": f"Bearer {token}"}

        for _ in range(30):
            response = client.post(
                "/feedback",
                json={"session_id": "s1", "message_id": str(uuid.uuid4()), "rating": "up"},
                headers=headers,
            )
            assert response.status_code == 200

        response = client.post(
            "/feedback",
            json={"session_id": "s1", "message_id": str(uuid.uuid4()), "rating": "up"},
            headers=headers,
        )
        assert response.status_code == 429
        assert "detail" in response.json()
