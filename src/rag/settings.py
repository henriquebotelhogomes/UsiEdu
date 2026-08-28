"""Configurações do pipeline de RAG via variáveis de ambiente."""

from pydantic_settings import BaseSettings


class RagSettings(BaseSettings):
    """Configurações do pipeline de RAG.

    Carregadas de variáveis de ambiente ou arquivo .env.
    """

    model_config = {"env_prefix": ""}

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_academico: str = "academico"
    qdrant_collection_institucional: str = "institucional"

    # Embeddings
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_batch_size: int = 64

    # Reranker
    reranker_model: str = "BAAI/bge-reranker-base"

    # Chunking & Contextual Retrieval (Padrão Anthropic)
    chunk_max_chars: int = 3200  # ~800 tokens (estimativa: 4 chars/token)
    chunk_overlap_chars: int = 480  # ~15% do chunk_max_chars
    enable_contextual_retrieval: bool = True

    # Retrieval
    search_top_k: int = 20
    rerank_top_k: int = 5

    # Corrective RAG (CRAG) & Grader
    min_relevance_score: float = 0.35
    enable_crag_filter: bool = True

    @property
    def collections(self) -> dict[str, str]:
        """Retorna {perfil: nome_coleção}."""
        return {
            "student": self.qdrant_collection_academico,
            "staff": self.qdrant_collection_institucional,
        }
