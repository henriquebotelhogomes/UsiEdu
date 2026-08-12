"""Limites isolados de integração exercitados pela T03.1."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient, models

from src.rag.retriever import HybridRetriever
from src.storage.database import postgres_connection

ROOT = Path(__file__).parent.parent.parent
NGINX_TEMPLATE = ROOT / "frontend" / "nginx" / "default.conf.template"
DELIVERY_DOC = ROOT / "docs" / "profissionalizacao" / "03-integracao-entrega-rollback.md"


class _Embedder:
    def embed_query(self, text: str) -> list[float]:
        assert text
        return [1.0, 0.0]


@pytest.fixture
def isolated_qdrant() -> QdrantClient:
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name="academico_test",
        vectors_config=models.VectorParams(size=2, distance=models.Distance.COSINE),
    )
    client.upsert(
        collection_name="academico_test",
        points=[
            models.PointStruct(
                id=1,
                vector=[1.0, 0.0],
                payload={
                    "text": "O calendário acadêmico informa o início das aulas.",
                    "publico_alvo": "student",
                    "documento": "Calendário",
                    "secao": "Início das aulas",
                    "url_fonte": "https://example.invalid/calendario",
                },
            )
        ],
    )
    yield client
    client.close()


@pytest.fixture
def api_client_with_fake_graph(chat_graph) -> TestClient:
    from src.api import chat as chat_module
    from src.api.main import app

    previous = chat_module._graph
    chat_module._graph = chat_graph
    try:
        yield TestClient(app)
    finally:
        chat_module._graph = previous


def _login(client: TestClient) -> str:
    response = client.post(
        "/auth/login",
        json={"email": "ana@demo.usiedu", "password": "estudante123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_nginx_routes_api_and_disables_sse_buffering() -> None:
    config = NGINX_TEMPLATE.read_text(encoding="utf-8")

    for location in ("/auth/", "/chat", "/chat/stream", "/feedback", "/health"):
        assert f"location {location}" in config
    stream_block = config.split("location /chat/stream", maxsplit=1)[1].split(
        "location /chat", maxsplit=1
    )[0]
    assert "proxy_pass ${UPSTREAM_API_URL};" in stream_block
    assert "proxy_http_version 1.1;" in stream_block
    assert "proxy_buffering off;" in stream_block
    assert "proxy_cache off;" in stream_block
    assert "chunked_transfer_encoding on;" in stream_block
    assert "error_page" not in stream_block


def test_api_boundary_success_includes_unbuffered_sse_headers(
    api_client_with_fake_graph: TestClient,
) -> None:
    client = api_client_with_fake_graph
    assert client.get("/health").json()["status"] == "ok"
    token = _login(client)

    with client.stream(
        "POST",
        "/chat/stream",
        json={"session_id": "integration-sse", "message": "Quero ver minhas notas"},
        headers={"Authorization": f"Bearer {token}"},
    ) as response:
        body = "\n".join(response.iter_lines())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-accel-buffering"] == "no"
    assert '"event": "meta"' in body
    assert '"event": "token"' in body
    assert '"event": "final"' in body


def test_api_boundary_dependency_failure_is_visible() -> None:
    from src.api import chat as chat_module
    from src.api.main import app

    previous = chat_module._graph
    chat_module._graph = None
    try:
        client = TestClient(app)
        token = _login(client)
        response = client.post(
            "/chat",
            json={"session_id": "integration-unavailable", "message": "Teste"},
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        chat_module._graph = previous

    assert response.status_code == 500
    assert "não inicializado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_postgres_boundary_success_and_unavailability_are_distinct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = object()

    @asynccontextmanager
    async def connected():
        yield connection

    async def connect_success(url: str):
        assert url == "postgresql://integration.invalid/usiedu"
        return connected()

    monkeypatch.setenv("USIEDU_DATABASE_URL", "postgresql://integration.invalid/usiedu")
    monkeypatch.setattr("psycopg.AsyncConnection.connect", connect_success)
    async with postgres_connection() as observed:
        assert observed is connection

    async def connect_failure(url: str):
        raise ConnectionError(f"PostgreSQL indisponível em {url}")

    monkeypatch.setattr("psycopg.AsyncConnection.connect", connect_failure)
    with pytest.raises(ConnectionError, match="PostgreSQL indisponível"):
        async with postgres_connection():
            pass


def test_qdrant_boundary_success_and_unavailability_are_distinct(
    isolated_qdrant: QdrantClient,
) -> None:
    retriever = HybridRetriever(
        client=isolated_qdrant,
        embedder=_Embedder(),
        collection_name="academico_test",
        search_top_k=5,
        rerank_top_k=5,
    )
    retriever.build_bm25_index()

    results = retriever.search("Quando começam as aulas?", profile="student")

    assert len(results) == 1
    assert results[0].source.document == "Calendário"

    unavailable = SimpleNamespace(
        scroll=lambda **kwargs: (_ for _ in ()).throw(ConnectionError("Qdrant indisponível")),
        query_points=lambda **kwargs: (_ for _ in ()).throw(ConnectionError("Qdrant indisponível")),
    )
    failing_retriever = HybridRetriever(
        client=unavailable,
        embedder=_Embedder(),
        collection_name="academico_test",
    )
    with pytest.raises(ConnectionError, match="Qdrant indisponível"):
        failing_retriever.build_bm25_index()


def test_documentation_preserves_t03_1_after_later_microtasks() -> None:
    document = DELIVERY_DOC.read_text(encoding="utf-8")

    assert "- [x] **T03.1 — Cobrir limites de integração**" in document
    assert "- [ ] **T03.1 — Cobrir limites de integração**" not in document
    assert "`tests/integration/test_delivery_boundaries.py`" in document
    assert "- [x] **T03.2 — Automatizar fluxo E2E**" in document
