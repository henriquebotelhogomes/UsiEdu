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


class HybridRetriever:
    """Retriever híbrido: busca vetorial no Qdrant + BM25 + reranking.

    Pipeline:
    1. Busca vetorial (Qdrant) → top-K candidatos
    2. Busca BM25 (rank_bm25) → top-K candidatos
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

        # 1. Busca vetorial
        query_vector = self.embedder.embed_query(query)
        vector_hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=self.search_top_k,
            query_filter=profile_filter,
        )

        # 2. Busca BM25
        bm25_results = self._bm25_search(query)

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
        tokenized = [self._tokenize(t) for t in texts]
        self._bm25 = BM25Okapi(tokenized)

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
        """Tokenização simples (lowercase + split por espaços)."""
        import re

        text = text.lower()
        return re.findall(r"\w+", text)
