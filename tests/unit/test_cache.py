"""Testes do cache semântico do chat (T9.2)."""

from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from src.rag.cache import (
    ChatCache,
    chave_cache,
    doc_version_atual,
    normalizar_pergunta,
    similaridade_cosseno,
)

PERGUNTA = "Quando começa o semestre 2026.2?"
RESPOSTA_FAKE = "O semestre letivo de 2026.2 começa em 10 de agosto de 2026."


class FakeEmbedder:
    """Embedder determinístico para testes (não carrega modelo)."""

    def __init__(self, vetores: dict[str, list[float]] | None = None) -> None:
        self._vetores = vetores or {}

    def embed_query(self, text: str) -> list[float]:
        return self._vetores.get(text, [1.0, 0.0, 0.0])


@pytest.fixture()
def cache_env(tmp_path, monkeypatch):
    """Banco do cache isolado em tmp + manifest controlado."""
    monkeypatch.setenv("USIEDU_CACHE_DB", str(tmp_path / "cache.db"))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"documents": []}), encoding="utf-8")
    monkeypatch.setenv("USIEDU_MANIFEST_PATH", str(manifest))
    return tmp_path


class TestNormalizacaoEChaves:
    def test_normalizar_remove_acentos_espacos_e_caixa(self) -> None:
        assert normalizar_pergunta("  Quais   FÉRIAS em 2026? ") == "quais ferias em 2026?"

    def test_chave_deterministica_e_sensivel_ao_perfil(self) -> None:
        q = normalizar_pergunta(PERGUNTA)
        assert chave_cache("student", q) == chave_cache("student", q)
        assert chave_cache("student", q) != chave_cache("staff", q)

    def test_chave_e_sha256_de_perfil_mais_pergunta(self) -> None:
        q = normalizar_pergunta(PERGUNTA)
        esperado = hashlib.sha256(f"student|{q}".encode("utf-8")).hexdigest()
        assert chave_cache("student", q) == esperado


class TestSimilaridade:
    def test_vetores_identicos(self) -> None:
        assert similaridade_cosseno([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)

    def test_vetores_ortogonais(self) -> None:
        assert similaridade_cosseno([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_vetor_nulo_retorna_zero(self) -> None:
        assert similaridade_cosseno([0, 0], [1, 1]) == 0.0


class TestDocVersion:
    def test_hash_do_manifest(self, cache_env) -> None:
        caminho = cache_env / "manifest.json"
        esperado = hashlib.sha256(caminho.read_bytes()).hexdigest()
        assert doc_version_atual(str(caminho)) == esperado

    def test_manifest_inexistente_retorna_vazio(self, tmp_path) -> None:
        assert doc_version_atual(str(tmp_path / "nao-existe.json")) == ""


class TestChatCache:
    async def test_hit_exato(self, cache_env) -> None:
        cache = ChatCache(embedder=FakeEmbedder())
        resposta = {
            "answer": RESPOSTA_FAKE,
            "agents": ["documental"],
            "sources": [],
            "intent": "institucional",
        }
        assert await cache.store("student", PERGUNTA, resposta)

        hit = await cache.lookup("student", PERGUNTA)
        assert hit is not None
        assert hit["exact"] is True
        assert hit["similarity"] == 1.0
        assert hit["answer"] == resposta
        assert cache.stats() == {"cache_hits": 1, "cache_misses": 0}

    async def test_hit_semantico_parafrase_leve(self, cache_env) -> None:
        vetores = {
            "paráfrase leve da pergunta": [0.99, 0.1, 0.0],  # cosseno ≈ 0.995
            "pergunta distante": [0.0, 1.0, 0.0],  # cosseno = 0.0
        }
        cache = ChatCache(embedder=FakeEmbedder(vetores))
        resposta = {"answer": RESPOSTA_FAKE, "agents": [], "sources": [], "intent": "institucional"}
        await cache.store("student", PERGUNTA, resposta)

        hit = await cache.lookup("student", "paráfrase leve da pergunta")
        assert hit is not None
        assert hit["exact"] is False
        assert hit["similarity"] >= 0.97
        assert hit["answer"] == resposta

        assert await cache.lookup("student", "pergunta distante") is None

    async def test_miss_por_perfil_diferente(self, cache_env) -> None:
        cache = ChatCache(embedder=FakeEmbedder())
        resposta = {"answer": RESPOSTA_FAKE, "agents": [], "sources": [], "intent": "institucional"}
        await cache.store("student", PERGUNTA, resposta)

        assert await cache.lookup("staff", PERGUNTA) is None
        assert cache.stats()["cache_misses"] == 1

    async def test_expiracao_por_ttl(self, cache_env, monkeypatch) -> None:
        cache = ChatCache(embedder=FakeEmbedder())
        resposta = {"answer": RESPOSTA_FAKE, "agents": [], "sources": [], "intent": "institucional"}
        await cache.store("student", PERGUNTA, resposta)

        monkeypatch.setenv("USIEDU_CACHE_TTL_DAYS", "-1")  # janela já expirou
        assert await cache.lookup("student", PERGUNTA) is None

    async def test_invalidacao_por_doc_version(self, cache_env) -> None:
        cache = ChatCache(embedder=FakeEmbedder())
        resposta = {"answer": RESPOSTA_FAKE, "agents": [], "sources": [], "intent": "institucional"}
        await cache.store("student", PERGUNTA, resposta, doc_version="versao-1")

        # Base de conhecimento mudou → entrada antiga não é servida
        assert await cache.lookup("student", PERGUNTA, doc_version="versao-2") is None
        assert await cache.lookup("student", PERGUNTA, doc_version="versao-1") is not None

    async def test_cache_desativado_por_env(self, cache_env, monkeypatch) -> None:
        monkeypatch.setenv("USIEDU_CACHE_ENABLED", "false")
        cache = ChatCache(embedder=FakeEmbedder())
        resposta = {"answer": RESPOSTA_FAKE, "agents": [], "sources": [], "intent": "institucional"}

        assert await cache.store("student", PERGUNTA, resposta) is False
        assert await cache.lookup("student", PERGUNTA) is None
        assert cache.stats() == {"cache_hits": 0, "cache_misses": 0}


class TestPoliticaDeCache:
    def test_resposta_cacheavel(self) -> None:
        from src.api.chat_common import resposta_cacheavel

        assert resposta_cacheavel("institucional", primeira_mensagem=True) is True
        assert resposta_cacheavel("institucional", primeira_mensagem=False) is False
        assert resposta_cacheavel("academico", primeira_mensagem=True) is False
        assert resposta_cacheavel("financeiro", primeira_mensagem=True) is False
        assert resposta_cacheavel("fora_de_escopo", primeira_mensagem=True) is False

    async def test_sessao_sem_historico_em_sessao_nova(self) -> None:
        from src.api.chat_common import sessao_sem_historico
        from src.llm.fake import FakeChatModel
        from src.orchestration.graph import create_chat_graph

        graph = create_chat_graph(router_llm=FakeChatModel(), agent_llm=FakeChatModel())
        assert await sessao_sem_historico(graph, "sessao-nova") is True


# === Integração nos endpoints /chat e /chat/stream ===


def _make_graph(intent: str = "institucional"):
    """Grafo fake com LLMs que contam chamadas (intent configurável)."""
    from src.llm.fake import FakeChatModel
    from src.orchestration.graph import create_chat_graph

    class LlmContado(FakeChatModel):
        chamadas: int = 0

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            self.chamadas += 1
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    router_llm = LlmContado(
        default_response=json.dumps({"intent": intent, "plan": None, "reasoning": "teste"})
    )
    agent_llm = LlmContado(default_response=RESPOSTA_FAKE)
    graph = create_chat_graph(router_llm=router_llm, agent_llm=agent_llm)
    return graph, router_llm, agent_llm


@pytest.fixture()
def client_cache(cache_env):
    """API com grafo fake + cache com embedder fake (isolado em tmp)."""
    import src.api.chat as chat_module
    from src.api.main import app
    from src.rag.cache import set_chat_cache

    client = TestClient(app)
    yield client, chat_module
    chat_module._graph = None
    set_chat_cache(None)


def _get_token(client: TestClient) -> str:
    response = client.post(
        "/auth/login",
        json={"email": "ana@demo.usiedu", "password": "estudante123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


class TestCacheNoEndpointChat:
    def test_segunda_pergunta_vem_do_cache_sem_llm(self, client_cache, monkeypatch) -> None:
        """Critério de aceite: mesma pergunta → resposta do cache, sem LLM."""
        from src.rag.cache import ChatCache, set_chat_cache

        client, chat_module = client_cache
        graph, router_llm, agent_llm = _make_graph("institucional")
        chat_module._graph = graph
        set_chat_cache(ChatCache(embedder=FakeEmbedder()))

        token = _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        r1 = client.post(
            "/chat",
            json={"session_id": "sess-cache-1", "message": PERGUNTA},
            headers=headers,
        )
        assert r1.status_code == 200
        assert r1.json()["from_cache"] is False
        chamadas_apos_primeira = router_llm.chamadas + agent_llm.chamadas
        assert chamadas_apos_primeira > 0

        # Outro usuário/pergunta idêntica em outra sessão → cache
        r2 = client.post(
            "/chat",
            json={"session_id": "sess-cache-2", "message": PERGUNTA},
            headers=headers,
        )
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["from_cache"] is True
        assert data2["answer"] == r1.json()["answer"]
        assert data2["message_id"] != r1.json()["message_id"]  # message_id novo
        assert router_llm.chamadas + agent_llm.chamadas == chamadas_apos_primeira

    def test_fora_de_escopo_nao_e_cacheado(self, client_cache) -> None:
        client, chat_module = client_cache
        graph, router_llm, agent_llm = _make_graph("fora_de_escopo")
        chat_module._graph = graph
        from src.rag.cache import ChatCache, set_chat_cache

        set_chat_cache(ChatCache(embedder=FakeEmbedder()))

        token = _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        body = {"session_id": "sess-fde-1", "message": "quem ganhou a copa?"}

        r1 = client.post("/chat", json=body, headers=headers)
        assert r1.status_code == 200
        chamadas = router_llm.chamadas

        r2 = client.post("/chat", json={**body, "session_id": "sess-fde-2"}, headers=headers)
        assert r2.json()["from_cache"] is False
        assert router_llm.chamadas > chamadas  # supervisor chamado de novo

    def test_cache_desativado_por_env(self, client_cache, monkeypatch) -> None:
        monkeypatch.setenv("USIEDU_CACHE_ENABLED", "false")
        client, chat_module = client_cache
        graph, router_llm, agent_llm = _make_graph("institucional")
        chat_module._graph = graph
        from src.rag.cache import ChatCache, set_chat_cache

        set_chat_cache(ChatCache(embedder=FakeEmbedder()))

        token = _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        for sessao in ("sess-off-1", "sess-off-2"):
            r = client.post(
                "/chat", json={"session_id": sessao, "message": PERGUNTA}, headers=headers
            )
            assert r.json()["from_cache"] is False
        assert router_llm.chamadas == 2  # LLM chamado nas duas


class TestCacheNoEndpointStream:
    def test_stream_hit_exibe_from_cache(self, client_cache) -> None:
        client, chat_module = client_cache
        graph, router_llm, agent_llm = _make_graph("institucional")
        chat_module._graph = graph
        from src.rag.cache import ChatCache, set_chat_cache

        set_chat_cache(ChatCache(embedder=FakeEmbedder()))

        token = _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Popula o cache via POST /chat
        r1 = client.post(
            "/chat", json={"session_id": "sess-st-c1", "message": PERGUNTA}, headers=headers
        )
        assert r1.status_code == 200
        chamadas = router_llm.chamadas + agent_llm.chamadas

        # Mesma pergunta via stream → eventos sintéticos do cache
        r2 = client.post(
            "/chat/stream",
            json={"session_id": "sess-st-c2", "message": PERGUNTA},
            headers=headers,
        )
        assert r2.status_code == 200
        eventos = {}
        for line in r2.text.splitlines():
            if line.startswith("data: "):
                evento = json.loads(line[len("data: ") :])
                eventos[evento["event"]] = evento
        assert eventos["final"]["from_cache"] is True
        assert eventos["final"]["answer"] == r1.json()["answer"]
        assert eventos["token"]["delta"] == r1.json()["answer"]
        assert router_llm.chamadas + agent_llm.chamadas == chamadas


class TestContadoresNoHealth:
    def test_health_expoe_contadores_do_cache(self, client_cache) -> None:
        client, _ = client_cache
        from src.api.main import app

        response = TestClient(app).get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "cache_hits" in data
        assert "cache_misses" in data
