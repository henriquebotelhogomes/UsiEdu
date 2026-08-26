"""Gera evidência de ingestão isolada e recuperação da T02.2."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

from src.rag.chunker import DocumentChunker
from src.rag.embedder import Embedder
from src.rag.ingest import ingest_document
from src.rag.retriever import HybridRetriever
from src.rag.settings import RagSettings

ROOT = Path(__file__).parent.parent.parent
INVENTORY_PATH = ROOT / "src" / "evaluation" / "corpus_t02_2.json"
MANIFEST_PATH = ROOT / "knowledge_base" / "manifest.json"
EVIDENCE_PATH = ROOT / "src" / "evaluation" / "evidencia_corpus_t02_2.json"
COLLECTION = "t02_2_corpus_20260812"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_sha256() -> str:
    return hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()


def _create_empty_collection(client: QdrantClient, dimension: int) -> None:
    existing = {collection.name for collection in client.get_collections().collections}
    if COLLECTION in existing:
        client.delete_collection(COLLECTION)
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
    )
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="publico_alvo",
        field_schema=PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="instituicao",
        field_schema=PayloadSchemaType.KEYWORD,
    )


def _retrieve(retriever: HybridRetriever, question: str) -> list[dict[str, Any]]:
    return [
        {
            "document": result.source.document,
            "section": result.source.section,
            "url": result.source.url,
            "score": result.score,
            "excerpt": result.source.excerpt,
        }
        for result in retriever.search(question, profile="staff")
    ]


def execute(qdrant_url: str) -> dict[str, Any]:
    """Executa duas ingestões na coleção isolada e registra recuperação antes/depois."""
    inventory = _load_json(INVENTORY_PATH)
    questions = {
        question_id: question["evaluation_question"]
        for question_id, question in inventory["questions"].items()
    }
    expected_behavior = {
        question_id: question["expected_behavior"]
        for question_id, question in inventory["questions"].items()
    }
    manifest = _load_json(MANIFEST_PATH)
    selected_files = {source["file"] for source in inventory["sources"]}
    documents = [
        dict(document) for document in manifest["documents"] if document["file"] in selected_files
    ]
    if {document["file"] for document in documents} != selected_files:
        raise ValueError("manifest nao contem todas as fontes inventariadas")

    settings = RagSettings(
        qdrant_url=qdrant_url,
        qdrant_collection_academico=COLLECTION,
        qdrant_collection_institucional=COLLECTION,
        search_top_k=25,
        rerank_top_k=25,
    )
    embedder = Embedder(
        model_name=settings.embedding_model,
        batch_size=settings.embedding_batch_size,
    )
    client = (
        QdrantClient(":memory:")
        if qdrant_url == ":memory:"
        else QdrantClient(url=qdrant_url, timeout=60.0)
    )
    _create_empty_collection(client, embedder.dimension)

    before_retriever = HybridRetriever(
        client=client,
        embedder=embedder,
        reranker=None,
        collection_name=COLLECTION,
        search_top_k=settings.search_top_k,
        rerank_top_k=settings.rerank_top_k,
    )
    before_retriever.build_bm25_index()
    before = {
        question_id: _retrieve(before_retriever, question)
        for question_id, question in questions.items()
    }
    chunker = DocumentChunker(
        max_chars=settings.chunk_max_chars,
        overlap_chars=settings.chunk_overlap_chars,
    )
    first_uploaded = sum(
        ingest_document(document, chunker, embedder, client, settings) for document in documents
    )
    first_points = client.get_collection(COLLECTION).points_count

    second_uploaded = sum(
        ingest_document(document, chunker, embedder, client, settings) for document in documents
    )
    second_points = client.get_collection(COLLECTION).points_count
    per_document = {document["name"]: document["chunks"] for document in documents}

    retriever = HybridRetriever(
        client=client,
        embedder=embedder,
        reranker=None,
        collection_name=COLLECTION,
        search_top_k=settings.search_top_k,
        rerank_top_k=settings.rerank_top_k,
    )
    retriever.build_bm25_index()
    retrieval = {
        question_id: {
            "question": question,
            "expected_behavior": expected_behavior[question_id],
            "before": before[question_id],
            "after": _retrieve(retriever, question),
        }
        for question_id, question in questions.items()
    }

    return {
        "schema_version": "1.1.0",
        "run_id": "t02-2-corpus-2026-08-12",
        "collection": COLLECTION,
        "manifest_sha256": _manifest_sha256(),
        "ingestion": {
            "first_run": {
                "uploaded_points": first_uploaded,
                "points_after": first_points,
                "per_document": per_document,
            },
            "second_run": {
                "uploaded_points": second_uploaded,
                "points_after": second_points,
            },
        },
        "retrieval": retrieval,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa evidência isolada da T02.2")
    parser.add_argument(
        "--qdrant-url",
        default="http://localhost:6333",
        help="URL do Qdrant ou :memory: para validação isolada local.",
    )
    parser.add_argument("--output", type=Path, default=EVIDENCE_PATH)
    args = parser.parse_args()
    evidence = execute(args.qdrant_url)
    args.output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Evidencia gerada em: {args.output}")


if __name__ == "__main__":
    main()
