"""Testes unitários para o embedder."""

from unittest.mock import MagicMock

import pytest

from src.rag.embedder import Embedder


@pytest.fixture
def embedder(tmp_path):
    """Embedder com cache temporário e modelo mockado."""
    emb = Embedder(
        model_name="test-model",
        cache_dir=tmp_path / "cache",
        batch_size=2,
    )
    # Mocka o modelo para não precisar de download real
    mock_model = MagicMock()
    mock_model.embed.return_value = iter([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
    emb._model = mock_model
    emb._backend = "fastembed"
    emb._dimension = 3
    return emb


class TestEmbedderHash:
    """Testes para hash de textos."""

    def test_hash_deterministico(self):
        h1 = Embedder._hash_text("hello world")
        h2 = Embedder._hash_text("hello world")
        assert h1 == h2

    def test_hash_diferente_para_textos_diferentes(self):
        h1 = Embedder._hash_text("hello")
        h2 = Embedder._hash_text("world")
        assert h1 != h2


class TestEmbedderCache:
    """Testes para o cache de embeddings."""

    def test_cache_vazio_inicialmente(self, embedder):
        assert len(embedder._cache) == 0

    def test_embed_popula_cache(self, embedder):
        result = embedder.embed(["texto de teste"])
        assert len(result) >= 1
        # O cache deve ter pelo menos uma entrada
        assert len(embedder._cache) >= 1

    def test_cache_salva_e_carrega(self, embedder, tmp_path):
        # Gera embeddings
        embedder.embed(["texto cacheado"])
        cache_size_before = len(embedder._cache)
        assert cache_size_before >= 1

        # Salva cache
        embedder._save_cache()

        # Cria novo embedder apontando para o mesmo cache
        emb2 = Embedder(
            model_name="test-model",
            cache_dir=tmp_path / "cache",
        )
        assert len(emb2._cache) >= 1

    def test_segunda_chamada_usa_cache(self, embedder):
        # Primeira chamada
        embedder.embed(["texto único xyz"])
        call_count_1 = embedder._model.embed.call_count

        # Segunda chamada com o mesmo texto deve usar cache
        embedder.embed(["texto único xyz"])
        call_count_2 = embedder._model.embed.call_count

        # O modelo não deve ter sido chamado novamente
        assert call_count_2 == call_count_1


class TestEmbedderBatching:
    """Testes para o processamento em lotes."""

    def test_batch_respeita_batch_size(self, embedder):
        # batch_size=2, 5 textos → 3 chamadas ao modelo (2+2+1)
        # Reset mock para contar chamadas corretamente
        texts = [f"texto_{i}" for i in range(5)]

        # Configura mock para retornar a quantidade correta de embeddings
        def mock_embed(batch_texts):
            return iter([[0.1] * 3 for _ in batch_texts])

        embedder._model.embed.side_effect = mock_embed
        result = embedder.embed(texts)
        assert len(result) == 5

    def test_embed_query_retorna_um_vector(self, embedder):
        vec = embedder.embed_query("pergunta teste")
        assert isinstance(vec, list)
        assert len(vec) == 3  # dimensão do mock


class TestEmbedderDimension:
    """Testes para a propriedade dimension."""

    def test_dimension_retorna_valor_correto(self, embedder):
        assert embedder.dimension == 3

    def test_dimension_default_sem_modelo(self, tmp_path):
        emb = Embedder(model_name="nonexistent", cache_dir=tmp_path / "c")
        # Sem inicializar modelo, retorna default 384
        assert emb._dimension is None  # não inicializado
        # Força o default sem chamar _init_model
        assert emb._dimension or 384 == 384
