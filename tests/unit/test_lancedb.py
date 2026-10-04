"""Testes unitários para o armazenamento vetorial serverless LanceDB e HybridRetriever."""

from unittest.mock import MagicMock

import pytest

from src.rag.lancedb_store import LanceDBStore
from src.rag.models import Chunk
from src.rag.retriever import HybridRetriever


@pytest.fixture
def temp_lancedb(tmp_path):
    """Fixture que cria uma instância temporária do LanceDBStore."""
    db_dir = tmp_path / "lancedb_test"
    return LanceDBStore(db_path=db_dir)


@pytest.fixture
def sample_chunks():
    """Gera chunks de exemplo para teste."""
    chunks = [
        Chunk(
            id="chunk-1",
            text="Regulamento de matrícula da UnB para estudantes de graduação.",
            metadata={
                "documento": "Regimento_Geral",
                "titulo": "Matrícula",
                "publico_alvo": "student",
                "secao": "Art. 10",
                "instituicao": "UnB",
                "url_fonte": "https://unb.br/regimento",
            },
        ),
        Chunk(
            id="chunk-2",
            text="Diretrizes de afastamento para docentes e servidores técnicos.",
            metadata={
                "documento": "Manual_Servidor",
                "titulo": "Afastamento",
                "publico_alvo": "staff",
                "secao": "Capítulo II",
                "instituicao": "UnB",
                "url_fonte": "https://unb.br/servidores",
            },
        ),
        Chunk(
            id="chunk-3",
            text="Calendário acadêmico e datas de feriados institucionais para todos.",
            metadata={
                "documento": "Calendario_2026",
                "titulo": "Feriados",
                "publico_alvo": "all",
                "secao": "Anexo 1",
                "instituicao": "UnB",
                "url_fonte": "https://unb.br/calendario",
            },
        ),
    ]
    vectors = [
        [0.9, 0.1, 0.0, 0.0],
        [0.0, 0.9, 0.1, 0.0],
        [0.5, 0.5, 0.0, 0.0],
    ]
    return chunks, vectors


def test_lancedb_upsert_and_count(temp_lancedb, sample_chunks):
    """Testa inserção de chunks e contagem."""
    chunks, vectors = sample_chunks
    inserted = temp_lancedb.upsert_chunks("academico", chunks, vectors)
    assert inserted == 3
    assert temp_lancedb.count("academico") == 3


def test_lancedb_idempotency(temp_lancedb, sample_chunks):
    """Testa que reinserir os mesmos chunks não duplica registros."""
    chunks, vectors = sample_chunks
    temp_lancedb.upsert_chunks("academico", chunks, vectors)
    # Segunda inserção
    temp_lancedb.upsert_chunks("academico", chunks, vectors)
    assert temp_lancedb.count("academico") == 3


def test_lancedb_search_vector_with_student_filter(temp_lancedb, sample_chunks):
    """Testa busca vetorial filtrando por público-alvo student (student + all)."""
    chunks, vectors = sample_chunks
    temp_lancedb.upsert_chunks("academico", chunks, vectors)

    query_vec = [0.9, 0.1, 0.0, 0.0]
    results = temp_lancedb.search_vector("academico", query_vec, limit=5, profile="student")

    assert len(results) >= 1
    # Verifica que o resultado mais similar é o chunk-1
    assert results[0]["id"] == "chunk-1"
    assert results[0]["score"] > 0.8
    # Não deve retornar o chunk-2 (que é staff)
    ids = [r["id"] for r in results]
    assert "chunk-2" not in ids


def test_lancedb_search_vector_with_staff_filter(temp_lancedb, sample_chunks):
    """Testa busca vetorial filtrando por público-alvo staff (staff + all)."""
    chunks, vectors = sample_chunks
    temp_lancedb.upsert_chunks("institucional", chunks, vectors)

    query_vec = [0.0, 0.9, 0.1, 0.0]
    results = temp_lancedb.search_vector("institucional", query_vec, limit=5, profile="staff")

    assert len(results) >= 1
    assert results[0]["id"] == "chunk-2"
    ids = [r["id"] for r in results]
    assert "chunk-1" not in ids


def test_lancedb_get_all_documents_for_bm25(temp_lancedb, sample_chunks):
    """Testa extração de todos os documentos para construção do BM25."""
    chunks, vectors = sample_chunks
    temp_lancedb.upsert_chunks("academico", chunks, vectors)

    docs = temp_lancedb.get_all_documents("academico")
    assert len(docs) == 3
    doc_ids = {d[0] for d in docs}
    assert doc_ids == {"chunk-1", "chunk-2", "chunk-3"}


def test_lancedb_get_by_ids(temp_lancedb, sample_chunks):
    """Testa recuperação por IDs específicos."""
    chunks, vectors = sample_chunks
    temp_lancedb.upsert_chunks("academico", chunks, vectors)

    fetched = temp_lancedb.get_by_ids("academico", ["chunk-1", "chunk-3"])
    assert len(fetched) == 2
    fetched_ids = {f["id"] for f in fetched}
    assert fetched_ids == {"chunk-1", "chunk-3"}


def test_lancedb_delete_and_has_document(temp_lancedb, sample_chunks):
    """Testa verificação de existência e deleção por documento."""
    chunks, vectors = sample_chunks
    temp_lancedb.upsert_chunks("academico", chunks, vectors)

    assert temp_lancedb.has_document("academico", "Regimento_Geral") is True
    assert temp_lancedb.has_document("academico", "Inexistente") is False

    temp_lancedb.delete_document("academico", "Regimento_Geral")
    assert temp_lancedb.has_document("academico", "Regimento_Geral") is False
    assert temp_lancedb.count("academico") == 2


def test_hybrid_retriever_with_lancedb(temp_lancedb, sample_chunks):
    """Testa integração ponta a ponta do HybridRetriever usando LanceDBStore."""
    chunks, vectors = sample_chunks
    temp_lancedb.upsert_chunks("academico", chunks, vectors)

    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.9, 0.1, 0.0, 0.0]

    retriever = HybridRetriever(
        client=temp_lancedb,
        embedder=mock_embedder,
        collection_name="academico",
        search_top_k=5,
        rerank_top_k=3,
        enable_crag_filter=False,
    )
    retriever.build_bm25_index()

    results = retriever.search("matrícula estudante", profile="student")
    assert len(results) > 0
    assert results[0].source.document == "Regimento_Geral"
    assert "matrícula" in results[0].text.lower()
