"""Recuperação híbrida: busca vetorial + BM25 + reranking + filtro por perfil."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.rag.models import RetrievalResult, Source

if TYPE_CHECKING:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter

    from src.rag.embedder import Embedder
    from src.rag.reranker import Reranker

logger = logging.getLogger(__name__)

# Stopwords PT-BR: removidas na tokenização do BM25 (índice e query)
# para evitar que palavras funcionais dominem o ranking.
_STOPWORDS = {
    "a",
    "o",
    "e",
    "de",
    "da",
    "do",
    "das",
    "dos",
    "em",
    "no",
    "na",
    "nos",
    "nas",
    "um",
    "uma",
    "uns",
    "umas",
    "para",
    "por",
    "com",
    "sem",
    "sob",
    "sobre",
    "que",
    "se",
    "ao",
    "aos",
    "à",
    "às",
    "ou",
    "como",
    "mais",
    "menos",
    "já",
    "não",
    "sim",
    "ser",
    "ter",
    "está",
    "estão",
    "são",
    "foi",
    "sua",
    "seu",
    "suas",
    "seus",
    "este",
    "esta",
    "esse",
    "essa",
    "isto",
    "isso",
    "qual",
    "quais",
    "quando",
    "onde",
    "quem",
    "temos",
    "tenho",
    "tem",
    "têm",
    "pelo",
    "pela",
    "pelos",
    "pelas",
    "até",
    "entre",
    "após",
    "ante",
    "esse",
    "ano",
    "anos",
    "dia",
    "dias",
    "forma",
    "modo",
}


def _tokenize(text: str) -> list[str]:
    """Tokenização simples (lowercase + split por palavras) sem stopwords."""
    import re

    tokens = re.findall(r"\w+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


class HybridRetriever:
    """Retriever híbrido: busca vetorial no Qdrant + BM25 + reranking.

    Pipeline:
    1. Busca BM25 (rank_bm25) → top-K candidatos + termos de expansão
    2. Busca vetorial (Qdrant) com query expandida → top-K candidatos
    3. Fusão por Reciprocal Rank Fusion (RRF)
    4. Reranking com cross-encoder → top-N finais
    5. Filtro por perfil (via metadados do Qdrant)
    """

    def __init__(
        self,
        client: QdrantClient,
        embedder: Embedder,
        reranker: Reranker | None = None,
        collection_name: str = "academico",
        search_top_k: int = 20,
        rerank_top_k: int = 5,
    ) -> None:
        self.client = client
        self.embedder = embedder
        self.reranker = reranker
        self.collection_name = collection_name
        self.search_top_k = search_top_k
        self.rerank_top_k = rerank_top_k
        self._bm25_index: _BM25Index | None = None

    def search(
        self,
        query: str,
        profile: str = "student",
    ) -> list[RetrievalResult]:
        """Busca híbrida com filtro de perfil.

        Args:
            query: Pergunta do usuário.
            profile: "student" ou "staff" — filtra documentos por público-alvo.

        Returns:
            Lista de RetrievalResult ordenados por relevância.
        """
        profile_filter = self._build_profile_filter(profile)

        # 1. Busca BM25 (também fornece termos para expansão da query vetorial)
        bm25_results = self._bm25_search(query)

        # 2. Busca vetorial com query expandida por termos-chave do BM25:
        # perguntas curtas (ex: "quais feriados temos esse ano?") têm embedding
        # genérico; os termos dos top hits BM25 direcionam a busca vetorial
        expanded_query = self._expand_query(query, bm25_results)
        query_vector = self.embedder.embed_query(expanded_query)
        query_resp = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=self.search_top_k,
            query_filter=profile_filter,
        )
        vector_hits = query_resp.points

        # 3. Fusão RRF
        if bm25_results:
            fused_ids = self._reciprocal_rank_fusion(vector_hits, bm25_results)
            candidates = self._fetch_by_ids(fused_ids)
        else:
            candidates = [
                RetrievalResult(
                    text=hit.payload.get("text", ""),
                    score=hit.score,
                    source=self._make_source(hit.payload, hit.score),
                )
                for hit in vector_hits
            ]

        # 4. Reranking
        if self.reranker and candidates:
            candidates = self._apply_reranking(query, candidates)

        return candidates[: self.rerank_top_k]

    def build_bm25_index(self) -> None:
        """Constrói índice BM25 a partir dos documentos no Qdrant."""

        try:
            all_points, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False,
            )
        except Exception:
            logger.warning("Não foi possível construir índice BM25 (coleção vazia?).")
            return

        if not all_points:
            return

        docs = [(str(p.id), p.payload.get("text", "")) for p in all_points]
        self._bm25_index = _BM25Index(docs)
        logger.info("Índice BM25 construído com %d documentos.", len(docs))

    @staticmethod
    def _build_profile_filter(profile: str) -> Filter:
        """Constrói filtro do Qdrant por público-alvo."""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        return Filter(
            must=[
                FieldCondition(
                    key="publico_alvo",
                    match=MatchValue(value=profile),
                )
            ]
        )

    def _expand_query(self, query: str, bm25_results: list[tuple[str, float]]) -> str:
        """Expande a query com termos distintivos dos top hits do BM25.

        Extrai palavras frequentes nos melhores resultados BM25 que não
        estão na query original e as anexa, melhorando o ranqueamento
        vetorial para perguntas curtas ou coloquiais.
        """
        if self._bm25_index is None or not bm25_results:
            return query

        import re

        query_tokens = set(re.findall(r"\w+", query.lower()))

        top_ids = [doc_id for doc_id, _ in bm25_results[:3]]
        texts = self._bm25_index.get_texts(top_ids)

        freq: dict[str, int] = {}
        for text in texts:
            for token in set(re.findall(r"\w+", text.lower())):
                if len(token) >= 5 and token not in _STOPWORDS and token not in query_tokens:
                    freq[token] = freq.get(token, 0) + 1

        # Termos presentes em pelo menos 2 dos 3 top hits
        expansion = [t for t, c in freq.items() if c >= 2]
        if not expansion:
            return query

        expansion = sorted(expansion)[:8]
        logger.debug("Query expandida com termos BM25: %s", expansion)
        return f"{query} {' '.join(expansion)}"

    def _bm25_search(self, query: str) -> list[tuple[str, float]]:
        """Busca BM25 no índice local."""
        if self._bm25_index is None:
            return []
        return self._bm25_index.search(query, top_k=self.search_top_k)

    def _reciprocal_rank_fusion(
        self,
        vector_hits: list,
        bm25_results: list[tuple[str, float]],
    ) -> list[str]:
        """Reciprocal Rank Fusion (RRF) entre resultados vetoriais e BM25."""
        k = 60  # constante RRF
        scores: dict[str, float] = {}

        for rank, hit in enumerate(vector_hits):
            doc_id = str(hit.id)
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)

        for rank, (doc_id, _) in enumerate(bm25_results):
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)

        sorted_ids = sorted(scores, key=scores.get, reverse=True)
        return sorted_ids[: self.search_top_k]

    def _fetch_by_ids(self, ids: list[str]) -> list[RetrievalResult]:
        """Busca documentos específicos no Qdrant por ID."""
        if not ids:
            return []

        points = self.client.retrieve(
            collection_name=self.collection_name,
            ids=ids,
            with_payload=True,
        )

        points_map = {str(p.id): p for p in points}
        results = []
        for doc_id in ids:
            p = points_map.get(doc_id)
            if p and p.payload:
                results.append(
                    RetrievalResult(
                        text=p.payload.get("text", ""),
                        score=0.0,
                        source=self._make_source(p.payload, 0.0),
                    )
                )
        return results

    def _apply_reranking(
        self,
        query: str,
        candidates: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """Aplica reranking cross-encoder nos candidatos."""
        assert self.reranker is not None
        texts = [c.text for c in candidates]
        reranked = self.reranker.rerank(query, texts, top_k=self.rerank_top_k)
        return [
            RetrievalResult(
                text=candidates[idx].text,
                score=score,
                source=candidates[idx].source,
            )
            for idx, score in reranked
        ]

    @staticmethod
    def _make_source(payload: dict, score: float) -> Source:
        """Cria um Source a partir do payload do Qdrant."""
        return Source(
            document=payload.get("documento", ""),
            section=payload.get("secao"),
            excerpt=payload.get("text", ""),
            url=payload.get("url_fonte"),
        )


class _BM25Index:
    """Índice BM25 local usando rank_bm25."""

    def __init__(self, documents: list[tuple[str, str]]) -> None:
        """
        Args:
            documents: Lista de (doc_id, text).
        """
        from rank_bm25 import BM25Okapi

        self.ids = [doc_id for doc_id, _ in documents]
        texts = [text for _, text in documents]
        self._texts = {doc_id: text for doc_id, text in documents}
        tokenized = [self._tokenize(t) for t in texts]
        self._bm25 = BM25Okapi(tokenized)

    def get_texts(self, doc_ids: list[str]) -> list[str]:
        """Retorna os textos dos documentos pelos IDs."""
        return [self._texts[doc_id] for doc_id in doc_ids if doc_id in self._texts]

    def search(self, query: str, top_k: int = 20) -> list[tuple[str, float]]:
        """Busca BM25. Retorna lista de (doc_id, score)."""
        tokens = self._tokenize(query)
        scores = self._bm25.get_scores(tokens)

        indexed = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        return [(self.ids[i], float(s)) for i, s in indexed if s > 0]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenização simples (lowercase + split por palavras)."""
        return _tokenize(text)
