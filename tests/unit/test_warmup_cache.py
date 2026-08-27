"""Testes unitários para o script e catálogo de Semantic Cache Warmup."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from scripts.warmup_cache import warmup_semantic_cache
from src.rag.cache import ChatCache, set_chat_cache
from src.rag.faq_catalog import FAQ_CATALOG


class MockEmbedder:
    """Mock determinístico para geração de embeddings nos testes de warmup."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def embed_query(self, text: str) -> list[float]:
        # Vetor unitário determinístico baseado no hash do texto
        np.random.seed(abs(hash(text)) % (2**32))
        vec = np.random.randn(self.dim).astype(np.float32)
        norm = np.linalg.norm(vec)
        return (vec / (norm if norm > 0 else 1.0)).tolist()


class TestFAQCatalog:
    """Validações de integridade do catálogo canônico de FAQs."""

    def test_catalogo_tem_itens_validos(self) -> None:
        """O catálogo de FAQ deve conter itens não vazios."""
        assert len(FAQ_CATALOG) >= 10

    def test_todos_itens_possuem_campos_obrigatorios(self) -> None:
        """Cada item deve conter profile, question, answer, intent e sources."""
        for item in FAQ_CATALOG:
            assert item["profile"] in ("student", "staff")
            assert len(item["question"].strip()) > 10
            assert len(item["answer"].strip()) > 20
            assert item["intent"] in ("academico", "financeiro", "institucional")
            assert len(item["sources"]) >= 1


class TestWarmupSemanticCache:
    """Testes de execução do processo de pré-aquecimento de cache."""

    @pytest.mark.asyncio
    async def test_warmup_popula_cache_sqlite_e_permite_lookup(self) -> None:
        """Após o warmup, perguntas do catálogo devem retornar cache hit exato e semântico."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_db = str(Path(tmpdir) / "test_warmup.db")
            mock_emb = MockEmbedder()
            test_cache = ChatCache(embedder=mock_emb)
            set_chat_cache(test_cache)

            with patch("src.rag.cache._cache_db_path", return_value=temp_db):
                # Executa o warmup com limite de 5 itens
                count = await warmup_semantic_cache(
                    catalog=FAQ_CATALOG,
                    profile_filter="student",
                    clear_first=True,
                    dry_run=False,
                    limit=3,
                )
                assert count == 3

                # Testa lookup exato de um item aquecido
                item = FAQ_CATALOG[0]
                lookup_res = await test_cache.lookup(
                    profile=item["profile"],
                    question=item["question"],
                )
                assert lookup_res is not None
                assert lookup_res["from_cache"] is True
                assert lookup_res["exact"] is True
                assert lookup_res["answer"]["intent"] == item["intent"]

            set_chat_cache(None)

    @pytest.mark.asyncio
    async def test_warmup_dry_run_nao_grava_dados(self) -> None:
        """Modo dry-run deve retornar a contagem de itens sem gravar no banco de dados."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_db = str(Path(tmpdir) / "test_dry_run.db")
            with patch("src.rag.cache._cache_db_path", return_value=temp_db):
                count = await warmup_semantic_cache(
                    profile_filter="all",
                    dry_run=True,
                    limit=5,
                )
                assert count == 5
                # O arquivo do banco não deve ter sido criado
                assert not Path(temp_db).exists()

    @pytest.mark.asyncio
    async def test_warmup_filtra_por_perfil_staff(self) -> None:
        """Filtro por perfil staff deve aquecer apenas perguntas institucionais de staff."""
        staff_items = [i for i in FAQ_CATALOG if i["profile"] == "staff"]
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_db = str(Path(tmpdir) / "test_staff.db")
            mock_emb = MockEmbedder()
            test_cache = ChatCache(embedder=mock_emb)
            set_chat_cache(test_cache)

            with patch("src.rag.cache._cache_db_path", return_value=temp_db):
                count = await warmup_semantic_cache(
                    profile_filter="staff",
                    clear_first=True,
                    dry_run=False,
                )
                assert count == len(staff_items)

            set_chat_cache(None)
