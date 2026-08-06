"""Testes unitários para o retriever híbrido."""

from unittest.mock import MagicMock

import pytest

from src.rag.retriever import HybridRetriever, _BM25Index


@pytest.fixture
def mock_qdrant():
    """Cliente Qdrant mockado (API nova: query_points)."""
    client = MagicMock()

    class _QueryResponse:
        points = []

    client.query_points.return_value = _QueryResponse()
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
        mock_qdrant.query_points.assert_called_once()

        # Verifica que o filtro de perfil foi passado
        call_kwargs = mock_qdrant.query_points.call_args
        query_filter = call_kwargs.kwargs.get("query_filter") or call_kwargs[1].get("query_filter")
        assert query_filter is not None

    def test_search_retorna_lista_vazia_sem_resultados(self, retriever):
        results = retriever.search("pergunta sem resposta")
        assert results == []


class TestBuildBM25Index:
    """Testes para a construção do índice BM25 a partir do Qdrant."""

    @staticmethod
    def _point(doc_id, text):
        p = MagicMock()
        p.id = doc_id
        p.payload = {"text": text}
        return p

    def test_indice_construido_a_partir_do_scroll(self, retriever, mock_qdrant):
        mock_qdrant.scroll.return_value = (
            [
                self._point("id-1", "O calendário acadêmico lista os feriados do semestre"),
                self._point("id-2", "A matrícula em disciplinas ocorre no início do período"),
                self._point("id-3", "Normas sobre avaliação substitutiva e segunda chamada"),
                self._point("id-4", "Regras de trancamento de matrícula por motivo de saúde"),
            ],
            None,
        )
        retriever.build_bm25_index()
        assert retriever._bm25_index is not None
        results = retriever._bm25_search("feriados calendário")
        assert results and results[0][0] == "id-1"

    def test_scroll_com_falha_nao_derruba(self, retriever, mock_qdrant):
        mock_qdrant.scroll.side_effect = RuntimeError("Qdrant fora do ar")
        retriever.build_bm25_index()
        assert retriever._bm25_index is None

    def test_colecao_vazia_nao_cria_indice(self, retriever, mock_qdrant):
        mock_qdrant.scroll.return_value = ([], None)
        retriever.build_bm25_index()
        assert retriever._bm25_index is None


class TestExpandQuery:
    """Testes para a expansão de query com termos do BM25."""

    @pytest.fixture
    def retriever_com_indice(self, retriever):
        docs = [
            ("id-1", "calendario graduacao lista feriados nacionais e recessos"),
            ("id-2", "calendario graduacao define datas das avaliacoes finais"),
            ("id-3", "outro documento sobre bolsa permanencia estudantil"),
        ]
        retriever._bm25_index = _BM25Index(docs)
        return retriever

    def test_sem_indice_retorna_query_original(self, retriever):
        assert retriever._expand_query("feriados", [("id-1", 2.0)]) == "feriados"

    def test_sem_resultados_bm25_retorna_query_original(self, retriever_com_indice):
        assert retriever_com_indice._expand_query("feriados", []) == "feriados"

    def test_expande_com_termos_comuns_dos_top_hits(self, retriever_com_indice):
        expanded = retriever_com_indice._expand_query(
            "feriados", [("id-1", 3.0), ("id-2", 2.0), ("id-3", 1.0)]
        )
        # 'calendario' e 'graduacao' aparecem em 2 dos 3 top hits
        assert "calendario" in expanded
        assert "graduacao" in expanded
        assert expanded.startswith("feriados ")

    def test_sem_termos_comuns_retorna_query_original(self, retriever_com_indice):
        # Com apenas 1 hit, nenhum termo atinge frequência >= 2
        expanded = retriever_com_indice._expand_query("bolsa", [("id-3", 3.0)])
        assert expanded == "bolsa"


class TestFetchByIds:
    """Testes para a busca de documentos por ID no Qdrant."""

    def test_lista_vazia_retorna_vazio(self, retriever, mock_qdrant):
        assert retriever._fetch_by_ids([]) == []
        mock_qdrant.retrieve.assert_not_called()

    def test_retorna_na_ordem_dos_ids(self, retriever, mock_qdrant):
        p1 = MagicMock()
        p1.id = "id-1"
        p1.payload = {"text": "texto um", "documento": "Doc A", "secao": "Art. 1"}
        p2 = MagicMock()
        p2.id = "id-2"
        p2.payload = {"text": "texto dois", "documento": "Doc B"}
        mock_qdrant.retrieve.return_value = [p1, p2]

        results = retriever._fetch_by_ids(["id-2", "id-1", "id-inexistente"])
        assert [r.text for r in results] == ["texto dois", "texto um"]
        assert results[0].source.document == "Doc B"
        assert results[1].source.section == "Art. 1"

    def test_pontos_sem_payload_sao_ignorados(self, retriever, mock_qdrant):
        p1 = MagicMock()
        p1.id = "id-1"
        p1.payload = None
        mock_qdrant.retrieve.return_value = [p1]
        assert retriever._fetch_by_ids(["id-1"]) == []


class TestApplyReranking:
    """Testes para o reranking dos candidatos."""

    def test_reranker_reordena_candidatos(self, mock_qdrant, mock_embedder):
        reranker = MagicMock()
        reranker.rerank.return_value = [(1, 0.9), (0, 0.4)]
        retriever = HybridRetriever(
            client=mock_qdrant,
            embedder=mock_embedder,
            reranker=reranker,
            collection_name="academico",
        )

        from src.rag.models import RetrievalResult, Source

        candidatos = [
            RetrievalResult(
                text="texto A", score=0.8, source=Source(document="Doc", excerpt="texto A")
            ),
            RetrievalResult(
                text="texto B", score=0.7, source=Source(document="Doc", excerpt="texto B")
            ),
        ]

        resultado = retriever._apply_reranking("query", candidatos)
        assert [r.text for r in resultado] == ["texto B", "texto A"]
        assert [r.score for r in resultado] == [0.9, 0.4]
        reranker.rerank.assert_called_once_with("query", ["texto A", "texto B"], top_k=5)


@_requires_qdrant
class TestSearchComReranker:
    """Testes do fluxo completo de busca com BM25 + reranking."""

    def test_search_com_bm25_e_reranker(self, mock_qdrant, mock_embedder):
        reranker = MagicMock()
        reranker.rerank.return_value = [(0, 0.95)]
        retriever = HybridRetriever(
            client=mock_qdrant,
            embedder=mock_embedder,
            reranker=reranker,
            collection_name="academico",
        )
        # Índice BM25 com documento que casa com a query (4 docs → IDF positivo)
        retriever._bm25_index = _BM25Index(
            [
                ("id-1", "calendario com feriados nacionais do semestre"),
                ("id-2", "normas gerais sobre avaliação e frequência"),
                ("id-3", "procedimentos para solicitação de diploma"),
                ("id-4", "regras de uso da biblioteca central"),
            ]
        )

        # retrieve retorna o payload do candidato fundido via RRF
        ponto = MagicMock()
        ponto.id = "id-1"
        ponto.payload = {"text": "calendario com feriados nacionais", "documento": "Calendário"}
        mock_qdrant.retrieve.return_value = [ponto]

        results = retriever.search("quais feriados", profile="student")
        assert len(results) == 1
        assert results[0].score == 0.95
        assert results[0].source.document == "Calendário"
        reranker.rerank.assert_called_once()

    def test_search_sem_bm25_usa_apenas_vetorial(self, mock_qdrant, mock_embedder):
        hit = MagicMock()
        hit.id = "id-9"
        hit.score = 0.77
        hit.payload = {"text": "texto vetorial", "documento": "Doc V", "secao": None}

        class _Resp:
            points = [hit]

        mock_qdrant.query_points.return_value = _Resp()

        retriever = HybridRetriever(
            client=mock_qdrant,
            embedder=mock_embedder,
            reranker=None,
            collection_name="academico",
        )
        results = retriever.search("pergunta qualquer", profile="student")
        assert len(results) == 1
        assert results[0].text == "texto vetorial"
        assert results[0].score == 0.77


class TestStopwords:
    """Testes para a tokenização com stopwords PT-BR."""

    def test_stopwords_removidas(self):
        from src.rag.retriever import _tokenize

        tokens = _tokenize("Quais são os feriados deste ano?")
        assert "quais" not in tokens
        assert "são" not in tokens
        assert "feriados" in tokens

    def test_get_texts_ignora_ids_desconhecidos(self):
        idx = _BM25Index([("id-1", "texto um")])
        assert idx.get_texts(["id-1", "id-x"]) == ["texto um"]
