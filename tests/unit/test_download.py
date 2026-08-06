"""Testes unitários para o módulo de download de documentos."""

from unittest.mock import MagicMock

import pytest

from src.rag import download
from src.rag.download import compute_checksum, download_file, main


@pytest.fixture
def kb_dir(tmp_path, monkeypatch):
    """Redireciona knowledge_base/ e manifest.json para um diretório temporário."""
    kb = tmp_path / "knowledge_base"
    kb.mkdir()
    monkeypatch.setattr(download, "KNOWLEDGE_BASE_DIR", kb)
    monkeypatch.setattr(download, "MANIFEST_PATH", kb / "manifest.json")
    return kb


class TestComputeChecksum:
    """Testes para o checksum SHA-256."""

    def test_checksum_deterministico(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_bytes(b"conteudo de teste")
        assert compute_checksum(f) == compute_checksum(f)

    def test_checksum_formato_hex(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_bytes(b"abc")
        cs = compute_checksum(f)
        assert len(cs) == 64
        assert all(c in "0123456789abcdef" for c in cs)


class TestDownloadFile:
    """Testes para download_file com httpx mockado."""

    def test_arquivo_ja_existe_nao_baixa(self, tmp_path, monkeypatch):
        dest = tmp_path / "doc.pdf"
        dest.write_bytes(b"existente")
        stream_mock = MagicMock()
        monkeypatch.setattr(download.httpx, "stream", stream_mock)

        assert download_file("https://exemplo.br/doc.pdf", dest) is True
        stream_mock.assert_not_called()

    def test_download_sucesso(self, tmp_path, monkeypatch):
        dest = tmp_path / "doc.pdf"

        resp = MagicMock()
        resp.iter_bytes.return_value = [b"parte1-", b"parte2"]
        ctx = MagicMock()
        ctx.__enter__.return_value = resp
        ctx.__exit__.return_value = False
        stream_mock = MagicMock(return_value=ctx)
        monkeypatch.setattr(download.httpx, "stream", stream_mock)

        assert download_file("https://exemplo.br/doc.pdf", dest) is True
        assert dest.read_bytes() == b"parte1-parte2"
        resp.raise_for_status.assert_called_once()

    def test_download_falha_retorna_false(self, tmp_path, monkeypatch):
        dest = tmp_path / "doc.pdf"

        def _raise(*args, **kwargs):
            raise RuntimeError("sem rede")

        monkeypatch.setattr(download.httpx, "stream", _raise)

        assert download_file("https://exemplo.br/doc.pdf", dest) is False
        assert not dest.exists()


class TestMain:
    """Testes para o pipeline de download completo."""

    def test_main_baixa_e_atualiza_manifest(self, kb_dir, monkeypatch):
        manifest = {
            "documents": [
                {
                    "name": "Doc A",
                    "file": "doc_a.txt",
                    "url": "https://exemplo.br/a",
                    "publico_alvo": "student",
                }
            ]
        }
        import json

        (kb_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        resp = MagicMock()
        resp.iter_bytes.return_value = [b"conteudo A"]
        ctx = MagicMock()
        ctx.__enter__.return_value = resp
        ctx.__exit__.return_value = False
        monkeypatch.setattr(download.httpx, "stream", MagicMock(return_value=ctx))

        main()

        updated = json.loads((kb_dir / "manifest.json").read_text(encoding="utf-8"))
        assert updated["documents"][0]["checksum"]  # checksum gravado
        assert (kb_dir / "doc_a.txt").read_bytes() == b"conteudo A"

    def test_main_registra_falha_sem_derrubar(self, kb_dir, monkeypatch):
        manifest = {
            "documents": [
                {
                    "name": "Doc B",
                    "file": "doc_b.txt",
                    "url": "https://exemplo.br/b",
                    "publico_alvo": "student",
                }
            ]
        }
        import json

        (kb_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        def _raise(*args, **kwargs):
            raise RuntimeError("sem rede")

        monkeypatch.setattr(download.httpx, "stream", _raise)

        # Não deve lançar exceção mesmo com falha
        main()

        updated = json.loads((kb_dir / "manifest.json").read_text(encoding="utf-8"))
        assert "checksum" not in updated["documents"][0]
