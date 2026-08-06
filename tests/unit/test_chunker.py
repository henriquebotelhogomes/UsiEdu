"""Testes unitários para o chunker de documentos."""

import pytest

from src.rag.chunker import DocumentChunker
from src.rag.models import DocumentMetadata


@pytest.fixture
def chunker():
    return DocumentChunker(max_chars=200, overlap_chars=30)


@pytest.fixture
def metadata():
    return DocumentMetadata(
        instituicao="UnB",
        documento="Regimento Geral",
        publico_alvo="student",
        url_fonte="https://unb.br/regimento",
    )


class TestSplitText:
    """Testes para a divisão de texto em chunks."""

    def test_texto_curto_retorna_unico_chunk(self, chunker):
        text = "Texto curto que cabe em um chunk."
        parts = chunker._split_text(text)
        assert len(parts) == 1
        assert parts[0] == text

    def test_texto_longo_dividido(self, chunker):
        # 200 chars max → texto de 500 chars deve gerar múltiplos chunks
        text = "A" * 500
        parts = chunker._split_text(text)
        assert len(parts) >= 2

    def test_respeita_overlap(self, chunker):
        text = "Sentença um. " * 40  # ~520 chars
        parts = chunker._split_text(text)
        assert len(parts) >= 2
        # Verifica que há sobreposição: final do chunk 1 deve aparecer no chunk 2
        if len(parts) >= 2:
            # O overlap existe se o tamanho total > soma dos tamanhos individuais
            total_chars = sum(len(p) for p in parts)
            assert total_chars > len(text)  # overlap causa repetição

    def test_texto_vazio_retorna_lista_vazia(self, chunker):
        assert chunker._split_text("") == []
        assert chunker._split_text("   ") == []

    def test_quebra_em_limite_de_sentenca(self):
        chunker = DocumentChunker(max_chars=50, overlap_chars=5)
        # Texto longo o suficiente para forçar quebra (>50 chars)
        text = "Primeira sentença completa. Segunda sentença completa. Terceira sentença completa."
        parts = chunker._split_text(text)
        assert len(parts) >= 2
        # Cada parte deve ser não-vazia
        assert all(p.strip() for p in parts)


class TestDetectSections:
    """Testes para detecção de seções em documentos jurídicos."""

    def test_detecta_titulos_romanos(self, chunker):
        text = "Preâmbulo do documento.\nTÍTULO I\nDisposições iniciais.\nTÍTULO II\nDos direitos."
        sections = chunker._detect_sections(text)
        section_names = [name for name, _ in sections]
        assert "preâmbulo" in section_names
        assert "TÍTULO I" in section_names
        assert "TÍTULO II" in section_names

    def test_detecta_artigos(self, chunker):
        text = "Art. 1 Este regimento define as normas.\nArt. 2 São direitos dos estudantes."
        sections = chunker._detect_sections(text)
        section_names = [name for name, _ in sections]
        assert "Art. 1" in section_names
        assert "Art. 2" in section_names

    def test_detecta_capitulos(self, chunker):
        text = "CAPÍTULO I\nDas disposições gerais.\nCAPÍTULO II\nDos alunos."
        sections = chunker._detect_sections(text)
        section_names = [name for name, _ in sections]
        assert "CAPÍTULO I" in section_names
        assert "CAPÍTULO II" in section_names

    def test_sem_secoes_retorna_documento(self, chunker):
        text = "Texto corrido sem cabeçalhos de seção."
        sections = chunker._detect_sections(text)
        assert len(sections) == 1
        assert sections[0][0] == "documento"

    def test_texto_completo_preservado(self, chunker):
        text = "TÍTULO I\nConteúdo do título.\nArt. 1 Artigo primeiro."
        sections = chunker._detect_sections(text)
        combined = "".join(t for _, t in sections)
        # Todo o texto original deve estar presente
        assert "Conteúdo do título." in combined
        assert "Artigo primeiro." in combined


class TestMakeChunkId:
    """Testes para geração de IDs determinísticos."""

    def test_id_deterministico(self, metadata):
        id1 = DocumentChunker._make_chunk_id(metadata, 0)
        id2 = DocumentChunker._make_chunk_id(metadata, 0)
        assert id1 == id2

    def test_ids_diferentes_para_indices_diferentes(self, metadata):
        id1 = DocumentChunker._make_chunk_id(metadata, 0)
        id2 = DocumentChunker._make_chunk_id(metadata, 1)
        assert id1 != id2

    def test_id_formato_hex_16_chars(self, metadata):
        chunk_id = DocumentChunker._make_chunk_id(metadata, 0)
        assert len(chunk_id) == 16
        assert all(c in "0123456789abcdef" for c in chunk_id)


class TestChunkMetadata:
    """Testes para montagem de metadados nos chunks."""

    def test_chunks_tem_todos_metadados(self, chunker, metadata, tmp_path):
        # Cria arquivo de texto temporário
        doc = tmp_path / "teste.txt"
        doc.write_text("Texto de teste para verificar metadados completos dos chunks.")

        chunks = chunker.chunk_document(doc, metadata)
        assert len(chunks) >= 1

        chunk = chunks[0]
        assert chunk.metadata["instituicao"] == "UnB"
        assert chunk.metadata["documento"] == "Regimento Geral"
        assert chunk.metadata["publico_alvo"] == "student"
        assert chunk.metadata["url_fonte"] == "https://unb.br/regimento"
        assert "secao" in chunk.metadata
        assert "chunk_index" in chunk.metadata

    def test_ids_unicos(self, chunker, metadata, tmp_path):
        doc = tmp_path / "teste.txt"
        doc.write_text("A" * 500)  # Gera múltiplos chunks

        chunks = chunker.chunk_document(doc, metadata)
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))  # Todos únicos
