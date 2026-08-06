"""Reranking local com cross-encoder."""

from __future__ import annotations


class Reranker:
    """Reranker usando cross-encoder local (bge-reranker-base).

    Reordena candidatos de busca por relevância usando um modelo
    cross-encoder, que avalia pares (query, documento) diretamente.

    Documentos longos são divididos em janelas sobrepostas, pois o
    modelo trunca a entrada em ~512 tokens e a informação relevante
    pode estar além do início do texto.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
        window_chars: int = 1200,
        overlap_chars: int = 200,
    ) -> None:
        self.model_name = model_name
        self.window_chars = window_chars
        self.overlap_chars = overlap_chars
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

        # Pares (query, janela) com mapeamento janela → documento original
        pairs: list[tuple[str, str]] = []
        pair_to_doc: list[int] = []
        for doc_idx, doc in enumerate(documents):
            for window in self._windows(doc):
                pairs.append((query, window))
                pair_to_doc.append(doc_idx)

        raw_scores = self._model.predict(pairs)
        if hasattr(raw_scores, "tolist"):
            raw_scores = raw_scores.tolist()
        elif not isinstance(raw_scores, list):
            raw_scores = [float(raw_scores)]

        # Score do documento = melhor score entre suas janelas
        best: dict[int, float] = {}
        for doc_idx, score in zip(pair_to_doc, raw_scores):
            if doc_idx not in best or score > best[doc_idx]:
                best[doc_idx] = float(score)

        indexed = sorted(best.items(), key=lambda x: x[1], reverse=True)
        return indexed[:top_k]

    def _windows(self, text: str) -> list[str]:
        """Divide o texto em janelas sobrepostas para o cross-encoder."""
        if len(text) <= self.window_chars:
            return [text]
        windows = []
        step = self.window_chars - self.overlap_chars
        start = 0
        while start < len(text):
            windows.append(text[start : start + self.window_chars])
            start += step
        return windows
