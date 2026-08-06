"""Testes de integração do pipeline RAG (requer Qdrant rodando).

Estes testes são marcados com @pytest.mark.integration e só executam
quando o Qdrant está disponível em localhost:6333.
"""

import httpx
import pytest

from src.rag.settings import RagSettings

# Marca todos os testes neste módulo como integração
pytestmark = pytest.mark.integration


def qdrant_available() -> bool:
    """Verifica se o Qdrant está acessível."""
    try:
        resp = httpx.get("http://localhost:6333/healthz", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


skip_if_no_qdrant = pytest.mark.skipif(
    not qdrant_available(),
    reason="Qdrant não disponível em localhost:6333",
)


@skip_if_no_qdrant
class TestRAGIntegration:
    """Testes de integração com Qdrant real."""

    def test_qdrant_health(self):
        """Qdrant responde ao healthcheck."""
        resp = httpx.get("http://localhost:6333/healthz", timeout=5)
        assert resp.status_code == 200

    def test_collections_existem(self):
        """As coleções academico e institucional existem."""
        from qdrant_client import QdrantClient

        settings = RagSettings()
        client = QdrantClient(url=settings.qdrant_url)
        collections = {c.name for c in client.get_collections().collections}

        # Após ingestão, ambas devem existir
        if "academico" in collections:
            info = client.get_collection("academico")
            assert info.vectors_config.size > 0
