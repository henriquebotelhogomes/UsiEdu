"""Testes do endpoint de streaming SSE do chat (T7.3 — RF2-03)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient


def _get_token(client: TestClient) -> str:
    """Obtém token JWT para usuário demo."""
    response = client.post(
        "/auth/login",
        json={"email": "ana@demo.usiedu", "password": "estudante123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _make_fake_graph():
    """Cria grafo com LLMs fake (que streamam chunks determinísticos)."""
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


def _parse_sse(lines: list[str]) -> list[dict]:
    """Extrai os payloads JSON das linhas `data: {...}` do stream SSE."""
    events = []
    for line in lines:
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


class TestChatStream:
    """Testes do endpoint POST /chat/stream."""

    def test_stream_sem_token_retorna_401(self) -> None:
        """Streaming sem token deve retornar 401."""
        from src.api.main import app

        client = TestClient(app)
        response = client.post(
            "/chat/stream",
            json={"session_id": "sess-st-1", "message": "Quero ver minhas notas"},
        )
        assert response.status_code == 401

    def test_stream_sem_grafo_retorna_500(self) -> None:
        """Streaming sem grafo inicializado deve retornar 500."""
        from src.api import chat as chat_module
        from src.api.main import app

        chat_module._graph = None

        client = TestClient(app)
        token = _get_token(client)
        response = client.post(
            "/chat/stream",
            json={"session_id": "sess-st-2", "message": "Quero ver minhas notas"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 500
        assert "não inicializado" in response.json()["detail"]

    def test_stream_eventos_na_ordem_e_conteudo_completo(self) -> None:
        """Eventos chegam na ordem meta → token(s) → final; tokens concatenam
        para a resposta completa; tokens do supervisor não vazam."""
        from src.api import chat as chat_module
        from src.api.main import app

        chat_module._graph = _make_fake_graph()

        client = TestClient(app)
        token = _get_token(client)
        with client.stream(
            "POST",
            "/chat/stream",
            json={"session_id": "sess-st-3", "message": "Quero ver minhas notas"},
            headers={"Authorization": f"Bearer {token}"},
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            events = _parse_sse(list(response.iter_lines()))

        # Ordem: meta primeiro, final último
        assert events[0]["event"] == "meta"
        assert events[0]["session_id"] == "sess-st-3"
        assert events[0]["message_id"]  # run_id uuid4
        assert events[-1]["event"] == "final"

        # Tokens: apenas do nó final (nada de JSON do supervisor)
        tokens = [e for e in events if e["event"] == "token"]
        assert len(tokens) >= 1
        streamed = "".join(t["delta"] for t in tokens)
        assert "intent" not in streamed  # raciocínio do supervisor não vaza
        assert streamed.strip() == "Resposta fake do agente."

        # Final: conteúdo reconcilia com os tokens + agentes/fontes/uso
        final = events[-1]
        assert final["answer"] == streamed.strip()
        assert final["agents"] == ["academico"]
        assert isinstance(final["sources"], list)
        assert final["usage"]["intent"] == "academico"

    def test_stream_erro_emite_evento_error(self) -> None:
        """Exceção durante o stream deve emitir evento `error` e fechar."""
        from src.api import chat as chat_module
        from src.api.main import app

        class BrokenGraph:
            async def astream_events(self, *args, **kwargs):
                msg = "falha simulada"
                raise RuntimeError(msg)
                yield  # pragma: no cover — torna a função um gerador assíncrono

            async def aget_state(self, config):  # pragma: no cover
                return None

        chat_module._graph = BrokenGraph()

        client = TestClient(app)
        token = _get_token(client)
        with client.stream(
            "POST",
            "/chat/stream",
            json={"session_id": "sess-st-4", "message": "Quero ver minhas notas"},
            headers={"Authorization": f"Bearer {token}"},
        ) as response:
            assert response.status_code == 200
            events = _parse_sse(list(response.iter_lines()))

        assert events[0]["event"] == "meta"
        assert events[-1]["event"] == "error"
        assert "falha simulada" in events[-1]["detail"]
