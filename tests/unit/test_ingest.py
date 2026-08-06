"""Testes unitários para funções utilitárias da ingestão."""

from src.rag.ingest import compute_file_checksum, load_manifest, pick_collection
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
