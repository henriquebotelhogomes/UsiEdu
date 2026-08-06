"""Reranking local com cross-encoder."""

from __future__ import annotations


class Reranker:
    """Reranker usando cross-encoder local (bge-reranker-base).

    Reordena candidatos de busca por relevância usando um modelo
    cross-encoder, que avalia pares (query, documento) diretamente.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-base") -> None:
        self.model_name = model_name
        self._model = None

    def _init_model(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(self.model_name)

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 5,
    ) -> list[tuple[int, float]]:
        """Reordena documentos por relevância à query.

        Returns:
            Lista de (índice_original, score) ordenada por score descendente.
        """
        if not documents:
            return []

        self._init_model()
        assert self._model is not None

        pairs = [(query, doc) for doc in documents]
        scores = self._model.predict(pairs)

        # Normaliza scores para float (pode ser numpy array)
        if hasattr(scores, "tolist"):
            scores = scores.tolist()
        elif not isinstance(scores, list):
            scores = [float(scores)]

        indexed = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True,
        )
        return indexed[:top_k]
