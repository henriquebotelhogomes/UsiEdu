"""CLI de ingestão de documentos para o Qdrant.

Uso: python -m src.rag.ingest
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path

from src.rag.chunker import DocumentChunker
from src.rag.embedder import Embedder
from src.rag.models import Chunk, DocumentMetadata
from src.rag.settings import RagSettings
from src.security.guardrails import detect_injection, separar_chunks_suspeitos

logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_DIR = Path("knowledge_base")
MANIFEST_PATH = KNOWLEDGE_BASE_DIR / "manifest.json"
_QDRANT_TIMEOUT_SECONDS = 60.0


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


def pick_collections(
    publico_alvo: str, settings: RagSettings, backend: str = "lancedb"
) -> list[str]:
    """Seleciona as coleções/tabelas com base no público-alvo do documento."""
    if backend == "lancedb":
        academico = settings.lancedb_table_academico
        institucional = settings.lancedb_table_institucional
    else:
        academico = settings.qdrant_collection_academico
        institucional = settings.qdrant_collection_institucional

    if publico_alvo == "all":
        return [academico, institucional]
    if publico_alvo == "staff":
        return [institucional]
    return [academico]


def pick_collection(
    publico_alvo: str, settings: RagSettings, backend: str = "lancedb"
) -> str:
    """Seleciona a coleção/tabela principal com base no público-alvo do documento."""
    return pick_collections(publico_alvo, settings, backend=backend)[0]


def documento_indexado(
    client, doc_entry: dict, settings: RagSettings, backend: str = "lancedb"
) -> bool:
    """Confirma que o documento do manifest realmente existe na base vetorial."""
    collections = pick_collections(
        doc_entry.get("publico_alvo", "student"), settings, backend=backend
    )
    if backend == "lancedb":
        for table_name in collections:
            if not client.has_document(table_name, doc_entry["name"]):
                return False
        return True

    return documento_indexado_no_qdrant(client, doc_entry, settings)


def documento_indexado_no_qdrant(client, doc_entry: dict, settings: RagSettings) -> bool:
    """Confirma que o documento do manifest realmente existe na coleção remota do Qdrant."""
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    collections = pick_collections(
        doc_entry.get("publico_alvo", "student"), settings, backend="qdrant"
    )
    for collection_name in collections:
        try:
            result = client.count(
                collection_name=collection_name,
                count_filter=Filter(
                    must=[
                        FieldCondition(
                            key="documento",
                            match=MatchValue(value=doc_entry["name"]),
                        )
                    ]
                ),
                exact=True,
            )
            if result.count == 0:
                return False
        except Exception:
            logger.warning(
                "Não foi possível confirmar o documento '%s' em '%s'; reindexando.",
                doc_entry["name"],
                collection_name,
            )
            return False
    return True


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


def _delete_documento(client, collection_name: str, doc_name: str) -> None:
    """Remove todos os pontos de um documento da coleção (evita órfãos pós-rechunk)."""
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    client.delete(
        collection_name=collection_name,
        points_selector=Filter(
            must=[FieldCondition(key="documento", match=MatchValue(value=doc_name))]
        ),
    )


def ingest_document(
    doc_entry: dict,
    chunker: DocumentChunker,
    embedder: Embedder,
    client,
    settings: RagSettings,
    force: bool = False,
    backend: str | None = None,
) -> int:
    """Processa e indexa um único documento. Retorna número de chunks indexados."""
    if backend is None:
        backend = (
            "lancedb"
            if client.__class__.__name__ == "LanceDBStore"
            or (hasattr(client, "upsert_chunks") and not hasattr(client, "upsert"))
            else "qdrant"
        )
    file_path = KNOWLEDGE_BASE_DIR / doc_entry["file"]

    if not file_path.exists():
        logger.warning("Arquivo não encontrado: %s — execute download primeiro.", file_path)
        return 0

    # Verifica idempotência por checksum
    current_checksum = compute_file_checksum(file_path)
    if (
        not force
        and doc_entry.get("checksum") == current_checksum
        and doc_entry.get("indexed")
        and documento_indexado(client, doc_entry, settings, backend=backend)
    ):
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

    # 1.5 Guardrail de ingestão (T9.3): chunks com padrões de injeção são
    # marcados suspicious=true e excluídos do índice, com log de auditoria.
    chunks, suspeitos = separar_chunks_suspeitos(chunks)
    for chunk in suspeitos:
        chunk.metadata["suspicious"] = True
        logger.warning(
            "Chunk excluído do índice por suspeita de injeção (guardrail T9.3)",
            extra={
                "guardrail_triggered": True,
                "origem": "ingest",
                "chunk_id": chunk.id,
                "documento": doc_entry["name"],
                "padroes": detect_injection(chunk.text),
            },
        )
    if suspeitos:
        logger.info(
            "  %d chunks suspeitos excluídos; %d seguem para indexação.",
            len(suspeitos),
            len(chunks),
        )
    if not chunks:
        logger.warning(
            "Todos os chunks de '%s' foram bloqueados pelo guardrail.", doc_entry["name"]
        )
        return 0

    # 2. Embeddings (com batching e cache)
    texts = [c.text for c in chunks]
    vectors = embedder.embed(texts)
    logger.info("  %d embeddings calculados.", len(vectors))

    # 3. Upload para o backend selecionado (LanceDB ou Qdrant)
    collections = pick_collections(doc_entry["publico_alvo"], settings, backend=backend)
    uploaded = 0
    for col_name in collections:
        if backend == "lancedb":
            client.delete_document(col_name, doc_entry["name"])
            up = client.upsert_chunks(col_name, chunks, vectors)
        else:
            _delete_documento(client, col_name, doc_entry["name"])
            up = upload_chunks(client, col_name, chunks, vectors)
        uploaded += up
        logger.info("  %d pontos enviados para '%s' (%s).", up, col_name, backend)

    # 4. Atualiza entrada do manifest
    doc_entry["checksum"] = current_checksum
    doc_entry["indexed"] = True
    doc_entry["chunks"] = len(chunks)

    return uploaded


def main(argv: list[str] | None = None) -> None:
    """Pipeline completo de ingestão."""
    settings = RagSettings()
    parser = argparse.ArgumentParser(
        prog="python -m src.rag.ingest",
        description="Ingere a base de conhecimento no LanceDB ou Qdrant.",
    )
    parser.add_argument(
        "--backend",
        choices=["lancedb", "qdrant"],
        default=settings.vector_store_backend,
        help="Backend de armazenamento vetorial (padrão: lancedb serverless).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Re-ingere todos os documentos e substitui os pontos já indexados. "
            "Necessário após mudanças no chunker, que alteram contagem e conteúdo dos chunks."
        ),
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

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

    if args.backend == "lancedb":
        from src.rag.lancedb_store import LanceDBStore

        client = LanceDBStore(db_path=settings.lancedb_path)
        logger.info("Conectado ao LanceDB serverless em '%s'.", settings.lancedb_path)
    else:
        from qdrant_client import QdrantClient

        client = QdrantClient(
            url=settings.qdrant_url,
            timeout=_QDRANT_TIMEOUT_SECONDS,
        )
        ensure_collections(client, embedder.dimension)
        logger.info("Conectado ao Qdrant em '%s'.", settings.qdrant_url)

    chunker = DocumentChunker(
        max_chars=settings.chunk_max_chars,
        overlap_chars=settings.chunk_overlap_chars,
        contextualize=settings.enable_contextual_retrieval,
    )

    # Processa cada documento
    total_chunks = 0
    for doc_entry in manifest["documents"]:
        chunks = ingest_document(
            doc_entry,
            chunker,
            embedder,
            client,
            settings,
            force=args.force,
            backend=args.backend,
        )
        total_chunks += chunks

    # Salva manifest atualizado (newline fixa LF: o hash da cadeia de eval
    # compara bytes crus contra texto normalizado CRLF->LF)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )

    logger.info("Ingestão completa: %d chunks indexados no total.", total_chunks)


if __name__ == "__main__":
    main()
