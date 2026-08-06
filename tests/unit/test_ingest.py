"""Testes unitários para funções utilitárias da ingestão."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.rag import ingest
from src.rag.ingest import (
    compute_file_checksum,
    ensure_collections,
    ingest_document,
    load_manifest,
    main,
    pick_collection,
    upload_chunks,
)
from src.rag.models import Chunk
from src.rag.settings import RagSettings


class TestComputeChecksum:
    """Testes para cálculo de checksum de arquivo."""

    def test_checksum_deterministico(self, tmp_path):
        f = tmp_path / "teste.txt"
        f.write_text("conteúdo de teste")
        cs1 = compute_file_checksum(f)
        cs2 = compute_file_checksum(f)
        assert cs1 == cs2

    def test_checksum_diferente_para_conteudos_diferentes(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("conteúdo A")
        f2.write_text("conteúdo B")
        assert compute_file_checksum(f1) != compute_file_checksum(f2)

    def test_checksum_formato_hex(self, tmp_path):
        f = tmp_path / "teste.txt"
        f.write_text("abc")
        cs = compute_file_checksum(f)
        assert len(cs) == 64  # SHA-256 hex
        assert all(c in "0123456789abcdef" for c in cs)


class TestPickCollection:
    """Testes para seleção de coleção por perfil."""

    def test_student_retorna_academico(self):
        settings = RagSettings()
        assert pick_collection("student", settings) == settings.qdrant_collection_academico

    def test_staff_retorna_institucional(self):
        settings = RagSettings()
        assert pick_collection("staff", settings) == settings.qdrant_collection_institucional

    def test_outro_retorna_academico(self):
        settings = RagSettings()
        assert pick_collection("other", settings) == settings.qdrant_collection_academico


class TestRagSettings:
    """Testes para configurações do RAG."""

    def test_defaults(self):
        settings = RagSettings()
        assert settings.qdrant_url == "http://localhost:6333"
        assert settings.qdrant_collection_academico == "academico"
        assert settings.qdrant_collection_institucional == "institucional"
        assert settings.embedding_model == "paraphrase-multilingual-MiniLM-L12-v2"
        assert settings.search_top_k == 20
        assert settings.rerank_top_k == 5

    def test_collections_property(self):
        settings = RagSettings()
        colls = settings.collections
        assert colls["student"] == "academico"
        assert colls["staff"] == "institucional"


class TestLoadManifest:
    """Testes para carregamento do manifest."""

    def test_manifest_existente(self):
        manifest = load_manifest()
        assert "documents" in manifest
        assert len(manifest["documents"]) == 4

    def test_manifest_tem_campos_obrigatorios(self):
        manifest = load_manifest()
        for doc in manifest["documents"]:
            assert "name" in doc
            assert "file" in doc
            assert "url" in doc
            assert "publico_alvo" in doc
            assert "instituicao" in doc


def _client_sem_colecoes():
    """Cliente Qdrant mockado sem coleções existentes."""
    client = MagicMock()
    client.get_collections.return_value = SimpleNamespace(collections=[])
    return client


class TestEnsureCollections:
    """Testes para criação de coleções no Qdrant."""

    def test_cria_colecoes_inexistentes_com_indices(self):
        client = _client_sem_colecoes()
        ensure_collections(client, dimension=384)
        assert client.create_collection.call_count == 2
        assert client.create_payload_index.call_count == 4  # 2 campos x 2 coleções
        nomes = [c.kwargs["collection_name"] for c in client.create_collection.call_args_list]
        assert "academico" in nomes
        assert "institucional" in nomes

    def test_nao_recria_colecoes_existentes(self):
        client = MagicMock()
        client.get_collections.return_value = SimpleNamespace(
            collections=[SimpleNamespace(name="academico"), SimpleNamespace(name="institucional")]
        )
        ensure_collections(client, dimension=384)
        client.create_collection.assert_not_called()


class TestUploadChunks:
    """Testes para o envio de chunks ao Qdrant."""

    @staticmethod
    def _make_chunk(i: int) -> Chunk:
        return Chunk(
            id=f"{i:032x}",
            text=f"texto do chunk {i}",
            metadata={"documento": "Doc", "publico_alvo": "student"},
        )

    def test_upload_unico_lote(self):
        client = MagicMock()
        chunks = [self._make_chunk(i) for i in range(3)]
        vectors = [[0.1, 0.2]] * 3
        uploaded = upload_chunks(client, "academico", chunks, vectors)
        assert uploaded == 3
        client.upsert.assert_called_once()

    def test_upload_em_multiplos_lotes(self):
        client = MagicMock()
        chunks = [self._make_chunk(i) for i in range(101)]
        vectors = [[0.1]] * 101
        uploaded = upload_chunks(client, "academico", chunks, vectors)
        assert uploaded == 101
        assert client.upsert.call_count == 2  # lotes de 100

    def test_payload_contem_texto_e_metadados(self):
        client = MagicMock()
        chunks = [self._make_chunk(0)]
        upload_chunks(client, "academico", chunks, [[0.1]])
        ponto = client.upsert.call_args.kwargs["points"][0]
        assert ponto.payload["text"] == "texto do chunk 0"
        assert ponto.payload["documento"] == "Doc"


@pytest.fixture
def kb_dir(tmp_path, monkeypatch):
    """Redireciona knowledge_base/ para um diretório temporário."""
    kb = tmp_path / "knowledge_base"
    kb.mkdir()
    monkeypatch.setattr(ingest, "KNOWLEDGE_BASE_DIR", kb)
    monkeypatch.setattr(ingest, "MANIFEST_PATH", kb / "manifest.json")
    return kb


class TestIngestDocument:
    """Testes para o processamento de um documento individual."""

    @staticmethod
    def _doc_entry(file_name="doc.txt"):
        return {
            "name": "Doc Teste",
            "file": file_name,
            "url": "https://exemplo.br/doc",
            "instituicao": "UnB",
            "publico_alvo": "student",
            "file_type": "txt",
        }

    def test_arquivo_inexistente_retorna_zero(self, kb_dir):
        entry = self._doc_entry("nao_existe.txt")
        resultado = ingest_document(entry, MagicMock(), MagicMock(), MagicMock(), RagSettings())
        assert resultado == 0

    def test_documento_ja_indexado_e_pulado(self, kb_dir):
        f = kb_dir / "doc.txt"
        f.write_text("conteúdo")
        entry = self._doc_entry()
        entry["checksum"] = compute_file_checksum(f)
        entry["indexed"] = True
        resultado = ingest_document(entry, MagicMock(), MagicMock(), MagicMock(), RagSettings())
        assert resultado == 0

    def test_fluxo_completo_indexa_e_atualiza_entry(self, kb_dir):
        f = kb_dir / "doc.txt"
        f.write_text("conteúdo do documento")
        entry = self._doc_entry()

        chunks = [
            Chunk(id=f"{i:032x}", text=f"chunk {i}", metadata={"documento": "Doc Teste"})
            for i in range(2)
        ]
        chunker = MagicMock()
        chunker.chunk_document.return_value = chunks
        embedder = MagicMock()
        embedder.embed.return_value = [[0.1, 0.2]] * 2
        client = MagicMock()

        resultado = ingest_document(entry, chunker, embedder, client, RagSettings())

        assert resultado == 2
        client.upsert.assert_called_once()
        # Coleção acadêmica para público student
        assert client.upsert.call_args.kwargs["collection_name"] == "academico"
        assert entry["indexed"] is True
        assert entry["chunks"] == 2
        assert entry["checksum"] == compute_file_checksum(f)

    def test_sem_chunks_retorna_zero(self, kb_dir):
        f = kb_dir / "doc.txt"
        f.write_text("conteúdo")
        entry = self._doc_entry()
        chunker = MagicMock()
        chunker.chunk_document.return_value = []
        resultado = ingest_document(entry, chunker, MagicMock(), MagicMock(), RagSettings())
        assert resultado == 0


class FakeEmbedder:
    """Embedder fake para testes do pipeline principal."""

    dimension = 4

    def __init__(self, model_name="", batch_size=32):
        pass

    def embed(self, texts):
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]


class TestMain:
    """Testes para o pipeline completo de ingestão."""

    def test_manifest_vazio_encerra_cedo(self, kb_dir, monkeypatch):
        (kb_dir / "manifest.json").write_text(json.dumps({"documents": []}), encoding="utf-8")

        def _explode(*args, **kwargs):
            raise AssertionError("Embedder não deveria ser criado")

        monkeypatch.setattr(ingest, "Embedder", _explode)
        main()  # deve retornar sem erro

    def test_pipeline_completo_indexa_documento(self, kb_dir, monkeypatch):
        (kb_dir / "doc.txt").write_text(
            "Art. 1º Este regimento define as normas. " * 10, encoding="utf-8"
        )
        manifest = {
            "documents": [
                {
                    "name": "Doc Teste",
                    "file": "doc.txt",
                    "url": "https://exemplo.br/doc",
                    "instituicao": "UnB",
                    "publico_alvo": "staff",
                    "file_type": "txt",
                }
            ]
        }
        (kb_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        monkeypatch.setattr(ingest, "Embedder", FakeEmbedder)

        client = _client_sem_colecoes()
        import qdrant_client

        monkeypatch.setattr(qdrant_client, "QdrantClient", lambda url="": client)

        main()

        updated = json.loads((kb_dir / "manifest.json").read_text(encoding="utf-8"))
        doc = updated["documents"][0]
        assert doc["indexed"] is True
        assert doc["chunks"] > 0
        # Público staff → coleção institucional
        nomes_criadas = [
            c.kwargs["collection_name"] for c in client.create_collection.call_args_list
        ]
        assert "institucional" in nomes_criadas
        assert client.upsert.call_args.kwargs["collection_name"] == "institucional"
