"""Embeddings locais com batching e cache em disco."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

# Caminho padrão do cache de embeddings
_DEFAULT_CACHE = Path(".cache/embeddings")


class Embedder:
    """Embeddings locais com FastEmbed (preferido) ou sentence-transformers.

    Características:
    - Batching para eficiência (configurável, default 64).
    - Cache em disco: embeddings já calculados não são recomputados.
    - IDs determinísticos por hash do conteúdo (idempotência).
    """

    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        cache_dir: Path = _DEFAULT_CACHE,
        batch_size: int = 64,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._cache_dir = cache_dir
        self._cache_file = cache_dir / f"{model_name}.npz"
        self._cache: dict[str, list[float]] = {}
        self._model = None
        self._backend: str = ""
        self._dimension: int | None = None
        self._load_cache()

    def _init_model(self) -> None:
        """Inicializa o modelo de embeddings (lazy loading)."""
        if self._model is not None:
            return

        try:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self.model_name)
            self._backend = "fastembed"
        except (ImportError, ValueError):
            from sentence_transformers import SentenceTransformer

            st_model = SentenceTransformer(self.model_name)
            self._model = st_model
            self._backend = "sentence_transformers"

        # Descobre a dimensão com um embedding de teste
        test = self._encode_batch(["dimensão teste"])
        self._dimension = len(test[0])

    def _encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Codifica um batch de textos usando o backend ativo."""
        if self._backend == "fastembed":
            results = list(self._model.embed(texts))
            return [r.tolist() if hasattr(r, "tolist") else list(r) for r in results]
        else:
            return self._model.encode(texts, normalize_embeddings=True).tolist()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed de uma lista de textos com cache e batching."""
        self._init_model()

        # Verifica cache
        hashes = [self._hash_text(t) for t in texts]
        embeddings: list[list[float] | None] = [self._cache.get(h) for h in hashes]

        # Identifica textos que precisam de embedding
        to_compute = [(i, t) for i, (t, e) in enumerate(zip(texts, embeddings)) if e is None]

        if to_compute:
            for batch_start in range(0, len(to_compute), self.batch_size):
                batch = to_compute[batch_start : batch_start + self.batch_size]
                batch_texts = [t for _, t in batch]
                batch_embeddings = self._encode_batch(batch_texts)

                for (i, _), emb in zip(batch, batch_embeddings):
                    embeddings[i] = emb
                    self._cache[hashes[i]] = emb

            self._save_cache()

        return [e for e in embeddings if e is not None]

    def embed_query(self, text: str) -> list[float]:
        """Embed de uma única query (para retrieval)."""
        result = self.embed([text])
        return result[0]

    @property
    def dimension(self) -> int:
        """Dimensão dos embeddings produzidos pelo modelo."""
        self._init_model()
        return self._dimension or 384

    def _load_cache(self) -> None:
        if self._cache_file.exists():
            try:
                data = np.load(self._cache_file, allow_pickle=False)
                hashes = list(data["hashes"])
                vectors = data["vectors"]
                self._cache = {h: v.tolist() for h, v in zip(hashes, vectors)}
            except Exception:
                self._cache = {}

    def _save_cache(self) -> None:
        if not self._cache:
            return
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        hashes = list(self._cache.keys())
        vectors = np.array([self._cache[h] for h in hashes], dtype=np.float32)
        np.savez_compressed(self._cache_file, hashes=hashes, vectors=vectors)

    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()
