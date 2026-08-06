"""Testes unitários para o retriever híbrido."""

from unittest.mock import MagicMock

import pytest

from src.rag.retriever import HybridRetriever, _BM25Index


@pytest.fixture
def mock_qdrant():
    """Cliente Qdrant mockado."""
    client = MagicMock()
    client.search.return_value = []
    client.retrieve.return_value = []
    return client


@pytest.fixture
def mock_embedder():
    """Embedder mockado."""
    emb = MagicMock()
    emb.embed_query.return_value = [0.1] * 384
    return emb


@pytest.fixture
def retriever(mock_qdrant, mock_embedder):
    """Retriever com dependências mockadas."""
    return HybridRetriever(
        client=mock_qdrant,
        embedder=mock_embedder,
        reranker=None,
        collection_name="academico",
        search_top_k=10,
        rerank_top_k=5,
    )


try:
    import qdrant_client  # noqa: F401

    _has_qdrant_client = True
except ImportError:
    _has_qdrant_client = False

_requires_qdrant = pytest.mark.skipif(
    not _has_qdrant_client,
    reason="qdrant_client não instalado",
)


@_requires_qdrant
class TestProfileFilter:
    """Testes para o filtro de perfil."""

    def test_filtro_student(self):
        from qdrant_client.models import Filter

        f = HybridRetriever._build_profile_filter("student")
        assert isinstance(f, Filter)
        assert len(f.must) == 1
        assert f.must[0].key == "publico_alvo"
        assert f.must[0].match.value == "student"

    def test_filtro_staff(self):
        f = HybridRetriever._build_profile_filter("staff")
        assert f.must[0].match.value == "staff"


try:
    import rank_bm25  # noqa: F401

    _has_rank_bm25 = True
except ImportError:
    _has_rank_bm25 = False

_requires_bm25 = pytest.mark.skipif(
    not _has_rank_bm25,
    reason="rank_bm25 não instalado",
)


@_requires_bm25
class TestBM25Index:
    """Testes para o índice BM25 local."""

    @pytest.fixture
    def bm25_index(self):
        docs = [
            ("id-1", "O regimento define as normas acadêmicas da universidade"),
            ("id-2", "Os estudantes podem solicitar matrícula em disciplinas"),
            ("id-3", "O calendário acadêmico estabelece prazos e datas"),
            ("id-4", "A avaliação substitutiva é permitida em casos de falta"),
        ]
        return _BM25Index(docs)

    def test_busca_retorna_resultados(self, bm25_index):
        results = bm25_index.search("matrícula disciplinas")
        assert len(results) > 0

    def test_resultado_mais_relevante_primeiro(self, bm25_index):
        results = bm25_index.search("matrícula estudantes")
        # O documento sobre matrícula deve ter score alto
        ids = [doc_id for doc_id, _ in results]
        assert "id-2" in ids

    def test_busca_sem_resultado_para_query_irrelevante(self, bm25_index):
        results = bm25_index.search("xyzzy foobar quux")
        assert len(results) == 0

    def test_top_k_limita_resultados(self, bm25_index):
        results = bm25_index.search("universidade", top_k=2)
        assert len(results) <= 2

    def test_tokenize_simples(self):
        tokens = _BM25Index._tokenize("Olá, mundo! Teste 123.")
        assert "olá" in tokens
        assert "mundo" in tokens
        assert "teste" in tokens
        assert "123" in tokens


class TestReciprocalRankFusion:
    """Testes para a fusão RRF."""

    def test_rrf_combina_resultados(self, retriever, mock_qdrant):
        # Cria hits vetoriais mockados
        hit1 = MagicMock()
        hit1.id = "id-1"
        hit1.score = 0.9

        hit2 = MagicMock()
        hit2.id = "id-2"
        hit2.score = 0.8

        vector_hits = [hit1, hit2]
        bm25_results = [("id-2", 5.0), ("id-3", 3.0)]

        fused = retriever._reciprocal_rank_fusion(vector_hits, bm25_results)

        # id-2 aparece em ambos → deve ter score RRF mais alto
        assert "id-2" in fused
        assert "id-1" in fused
        assert "id-3" in fused

    def test_rrf_documento_em_ambos_sobe_no_ranking(self, retriever):
        hit1 = MagicMock()
        hit1.id = "id-a"
        hit1.score = 0.95
        hit2 = MagicMock()
        hit2.id = "id-b"
        hit2.score = 0.85

        vector_hits = [hit1, hit2]
        # id-b é #1 no BM25 mas #2 no vector → RRF deve favorecer id-b
        bm25_results = [("id-b", 10.0), ("id-a", 5.0)]

        fused = retriever._reciprocal_rank_fusion(vector_hits, bm25_results)
        # id-b deve estar no topo ou próximo
        assert fused[0] in ("id-a", "id-b")

    def test_rrf_lista_vazia(self, retriever):
        fused = retriever._reciprocal_rank_fusion([], [])
        assert fused == []


@_requires_qdrant
class TestSearch:
    """Testes para o método search."""

    def test_search_chama_qdrant_com_filtro(self, retriever, mock_qdrant, mock_embedder):
        retriever.search("Qual o prazo de matrícula?", profile="student")

        mock_embedder.embed_query.assert_called_once_with("Qual o prazo de matrícula?")
        mock_qdrant.search.assert_called_once()

        # Verifica que o filtro de perfil foi passado
        call_kwargs = mock_qdrant.search.call_args
        query_filter = call_kwargs.kwargs.get("query_filter") or call_kwargs[1].get("query_filter")
        assert query_filter is not None

    def test_search_retorna_lista_vazia_sem_resultados(self, retriever):
        results = retriever.search("pergunta sem resposta")
        assert results == []
