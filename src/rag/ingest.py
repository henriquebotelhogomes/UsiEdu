"""CLI de ingestão de documentos para o Qdrant.

Uso: python -m src.rag.ingest
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from src.rag.chunker import DocumentChunker
from src.rag.embedder import Embedder
from src.rag.models import Chunk, DocumentMetadata
from src.rag.settings import RagSettings

logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_DIR = Path("knowledge_base")
MANIFEST_PATH = KNOWLEDGE_BASE_DIR / "manifest.json"


def load_manifest() -> dict:
    """Carrega o manifest.json com metadados dos documentos."""
    if not MANIFEST_PATH.exists():
        logger.error("Manifest não encontrado: %s", MANIFEST_PATH)
        return {"documents": []}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def compute_file_checksum(file_path: Path) -> str:
    """Calcula checksum SHA-256 de um arquivo."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_collections(client, dimension: int) -> None:
    """Cria coleções no Qdrant se não existirem."""
    from qdrant_client.models import (
        Distance,
        PayloadSchemaType,
        VectorParams,
    )

    settings = RagSettings()
    existing = {c.name for c in client.get_collections().collections}

    for collection_name in [
        settings.qdrant_collection_academico,
        settings.qdrant_collection_institucional,
    ]:
        if collection_name not in existing:
            logger.info("Criando coleção '%s'...", collection_name)
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
            # Índices para filtro por perfil
            client.create_payload_index(
                collection_name=collection_name,
                field_name="publico_alvo",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            client.create_payload_index(
                collection_name=collection_name,
                field_name="instituicao",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.info("Coleção '%s' criada com sucesso.", collection_name)
        else:
            logger.info("Coleção '%s' já existe.", collection_name)


def pick_collection(publico_alvo: str, settings: RagSettings) -> str:
    """Seleciona a coleção correta com base no público-alvo do documento."""
    if publico_alvo == "staff":
        return settings.qdrant_collection_institucional
    return settings.qdrant_collection_academico


def upload_chunks(
    client,
    collection_name: str,
    chunks: list[Chunk],
    vectors: list[list[float]],
) -> int:
    """Envia chunks para o Qdrant com idempotência."""
    import uuid

    from qdrant_client.models import PointStruct

    points = [
        PointStruct(
            id=uuid.UUID(hex=chunk.id.zfill(32)),
            vector=vector,
            payload={
                "text": chunk.text,
                **chunk.metadata,
            },
        )
        for chunk, vector in zip(chunks, vectors)
    ]

    # Upload em lotes de 100
    batch_size = 100
    uploaded = 0
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=collection_name, points=batch)
        uploaded += len(batch)

    return uploaded


def ingest_document(
    doc_entry: dict,
    chunker: DocumentChunker,
    embedder: Embedder,
    client,
    settings: RagSettings,
) -> int:
    """Processa e indexa um único documento. Retorna número de chunks indexados."""
    file_path = KNOWLEDGE_BASE_DIR / doc_entry["file"]

    if not file_path.exists():
        logger.warning("Arquivo não encontrado: %s — execute download primeiro.", file_path)
        return 0

    # Verifica idempotência por checksum
    current_checksum = compute_file_checksum(file_path)
    if doc_entry.get("checksum") == current_checksum and doc_entry.get("indexed"):
        logger.info("Documento '%s' já indexado (checksum igual). Pulando.", doc_entry["name"])
        return 0

    metadata = DocumentMetadata(
        instituicao=doc_entry["instituicao"],
        documento=doc_entry["name"],
        publico_alvo=doc_entry["publico_alvo"],
        url_fonte=doc_entry["url"],
        file_type=doc_entry["file_type"],
    )

    # 1. Chunking
    logger.info("Processando '%s'...", doc_entry["name"])
    chunks = chunker.chunk_document(file_path, metadata)
    if not chunks:
        logger.warning("Nenhum chunk gerado para '%s'.", doc_entry["name"])
        return 0

    logger.info("  %d chunks gerados.", len(chunks))

    # 2. Embeddings (com batching e cache)
    texts = [c.text for c in chunks]
    vectors = embedder.embed(texts)
    logger.info("  %d embeddings calculados.", len(vectors))

    # 3. Upload para Qdrant
    collection_name = pick_collection(doc_entry["publico_alvo"], settings)
    uploaded = upload_chunks(client, collection_name, chunks, vectors)
    logger.info("  %d pontos enviados para '%s'.", uploaded, collection_name)

    # 4. Atualiza entrada do manifest
    doc_entry["checksum"] = current_checksum
    doc_entry["indexed"] = True
    doc_entry["chunks"] = len(chunks)

    return uploaded


def main() -> None:
    """Pipeline completo de ingestão."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    settings = RagSettings()
    manifest = load_manifest()

    if not manifest.get("documents"):
        logger.error("Nenhum documento no manifest. Execute download primeiro:")
        logger.error("  python -m src.rag.download")
        return

    # Inicializa componentes
    embedder = Embedder(
        model_name=settings.embedding_model,
        batch_size=settings.embedding_batch_size,
    )

    from qdrant_client import QdrantClient

    client = QdrantClient(url=settings.qdrant_url)

    # Garante que as coleções existem
    ensure_collections(client, embedder.dimension)

    chunker = DocumentChunker(
        max_chars=settings.chunk_max_chars,
        overlap_chars=settings.chunk_overlap_chars,
    )

    # Processa cada documento
    total_chunks = 0
    for doc_entry in manifest["documents"]:
        chunks = ingest_document(doc_entry, chunker, embedder, client, settings)
        total_chunks += chunks

    # Salva manifest atualizado
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("Ingestão completa: %d chunks indexados no total.", total_chunks)


if __name__ == "__main__":
    main()
