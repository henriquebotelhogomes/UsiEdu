"""Sincroniza os índices vetoriais do Qdrant para o LanceDB Serverless (disco)."""

from __future__ import annotations

import logging
from pathlib import Path

from qdrant_client import QdrantClient

from src.rag.lancedb_store import LanceDBStore
from src.rag.models import Chunk

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def migrate_collection(
    qdrant_client: QdrantClient,
    lancedb_store: LanceDBStore,
    collection_name: str,
) -> int:
    """Extrai pontos e vetores do Qdrant e insere na tabela LanceDB."""
    logger.info("Iniciando migração da coleção '%s'...", collection_name)

    all_points = []
    offset = None

    while True:
        points, next_offset = qdrant_client.scroll(
            collection_name=collection_name,
            limit=200,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        if not points:
            break
        all_points.extend(points)
        if next_offset is None:
            break
        offset = next_offset

    if not all_points:
        logger.warning("Nenhum ponto encontrado na coleção '%s'.", collection_name)
        return 0

    logger.info("Recuperados %d pontos do Qdrant. Convertendo para LanceDB...", len(all_points))

    chunks: list[Chunk] = []
    vectors: list[list[float]] = []

    for p in all_points:
        payload = p.payload or {}
        chunk = Chunk(
            id=str(p.id),
            text=payload.get("text", ""),
            metadata={k: v for k, v in payload.items() if k != "text"},
        )
        chunks.append(chunk)
        # Vetor
        vec = p.vector
        if isinstance(vec, dict):
            # Vetores nomeados se houver
            vec = list(vec.values())[0]
        vectors.append(list(vec))

    inserted = lancedb_store.upsert_chunks(
        table_name=collection_name,
        chunks=chunks,
        vectors=vectors,
    )
    logger.info(
        "Migração de '%s' concluída com sucesso: %d chunks no LanceDB.",
        collection_name,
        inserted,
    )
    return inserted


def main() -> None:
    qdrant_url = "http://localhost:6333"
    lancedb_path = Path("data/lancedb")

    logger.info("Conectando ao Qdrant em '%s'...", qdrant_url)
    qdrant_client = QdrantClient(qdrant_url, timeout=30.0)

    logger.info("Conectando ao LanceDB em '%s'...", lancedb_path)
    lancedb_store = LanceDBStore(db_path=lancedb_path)

    for col in ["academico", "institucional"]:
        migrate_collection(qdrant_client, lancedb_store, col)

    logger.info("--- Validação Pós-Migração ---")
    logger.info("Contagem LanceDB academico: %d", lancedb_store.count("academico"))
    logger.info("Contagem LanceDB institucional: %d", lancedb_store.count("institucional"))
    logger.info("Base vetorial LanceDB Serverless pronta para uso em produção!")


if __name__ == "__main__":
    main()
