"""Testes unitários para o chunker de documentos."""

import re
from pathlib import Path

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

    def test_progresso_garantido_com_overlap_grande(self):
        """Overlap >= max_chars não pode causar loop infinito."""
        chunker = DocumentChunker(max_chars=10, overlap_chars=10)
        # Sem pontuação/quebras: não há ponto de quebra além do limite
        parts = chunker._split_text("a" * 35)
        assert len(parts) >= 3
        assert "".join(parts).count("a") >= 35


class TestExtractText:
    """Testes para extração de texto por tipo de arquivo."""

    def test_arquivo_vazio_retorna_chunks_vazios(self, chunker, metadata, tmp_path):
        f = tmp_path / "vazio.txt"
        f.write_text("   \n\n  ")
        assert chunker.chunk_document(f, metadata) == []

    def test_txt_lido_diretamente(self, chunker, metadata, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("Conteúdo de teste do documento.", encoding="utf-8")
        chunks = chunker.chunk_document(f, metadata)
        assert len(chunks) == 1
        assert "Conteúdo de teste" in chunks[0].text
        assert chunks[0].metadata["publico_alvo"] == "student"

    def test_extracao_html_utf8(self, chunker, metadata, tmp_path):
        f = tmp_path / "pagina.html"
        f.write_text(
            "<html><head><title>Normas</title></head><body>"
            "<article>"
            "<p>O regimento geral estabelece as normas acadêmicas da universidade.</p>"
            "<p>Os estudantes devem observar os prazos definidos no calendário.</p>"
            "</article></body></html>",
            encoding="utf-8",
        )
        text = chunker._extract_text(f)
        assert isinstance(text, str)

    def test_extracao_html_latin1_fallback(self, chunker, tmp_path):
        f = tmp_path / "pagina_latin1.html"
        # Byte 0xE9 (é em latin-1) é inválido como UTF-8 isolado
        f.write_bytes(b"<html><body><p>Caf\xe9 com a\xe7\xfacar.</p></body></html>")
        text = chunker._extract_text(f)
        assert isinstance(text, str)  # não lança UnicodeDecodeError

    def test_extracao_pdf(self, chunker, metadata, tmp_path):
        fitz = pytest.importorskip("fitz")
        pdf_path = tmp_path / "calendario.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Calendario academico 2026")
        page.insert_text((72, 100), "Feriados nacionais do semestre")
        doc.save(str(pdf_path))
        doc.close()

        text = chunker._extract_text(pdf_path)
        assert "Calendario academico 2026" in text
        assert "Feriados nacionais" in text

        chunks = chunker.chunk_document(pdf_path, metadata)
        assert len(chunks) >= 1


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


class TestContextualRetrieval:
    """Testes para o Contextual Retrieval (Padrão Anthropic)."""

    def test_prefixo_contextual_adicionado_quando_habilitado(self, metadata, tmp_path):
        chunker = DocumentChunker(max_chars=500, overlap_chars=50, contextualize=True)
        doc = tmp_path / "regimento.txt"
        doc.write_text(
            "Art. 10 O trancamento de matrícula é permitido até o 30º dia do semestre letivo.",
            encoding="utf-8",
        )

        chunks = chunker.chunk_document(doc, metadata)
        assert len(chunks) == 1
        chunk = chunks[0]

        # Verifica se o prefixo de ancoragem contextual está presente no texto vetorizado
        assert "Este trecho pertence ao documento 'Regimento Geral'" in chunk.text
        assert "da instituição 'UnB'" in chunk.text
        assert "seção 'Art. 10'" in chunk.text
        assert "O trancamento de matrícula é permitido" in chunk.text

        # Verifica se o texto original limpo foi preservado em metadata
        assert "original_text" in chunk.metadata
        assert "Este trecho pertence" not in chunk.metadata["original_text"]
        assert "Art. 10 O trancamento de matrícula" in chunk.metadata["original_text"]

    def test_sem_contextualizacao_quando_desabilitado(self, metadata, tmp_path):
        chunker = DocumentChunker(max_chars=500, overlap_chars=50, contextualize=False)
        doc = tmp_path / "regimento.txt"
        doc.write_text(
            "Art. 10 O trancamento de matrícula é permitido.",
            encoding="utf-8",
        )

        chunks = chunker.chunk_document(doc, metadata)
        assert len(chunks) == 1
        chunk = chunks[0]

        assert "Este trecho pertence" not in chunk.text
        assert chunk.text.startswith("Art. 10")
        assert chunk.metadata["original_text"] == chunk.text

    def test_build_context_prefix_variacoes(self, metadata):
        # 1. Seção padrão
        p1 = DocumentChunker._build_context_prefix(metadata, "Art. 42")
        assert "seção 'Art. 42'" in p1

        # 2. Preâmbulo
        p2 = DocumentChunker._build_context_prefix(metadata, "preâmbulo")
        assert "preâmbulo introdutório" in p2

        # 3. Documento sem seção específica
        p3 = DocumentChunker._build_context_prefix(metadata, "documento")
        assert "seção" not in p3


class TestHierarchicalParentDocument:
    """Testes para suporte a Parent-Document Retrieval (Small-to-Big)."""

    def test_parent_text_preservado_no_metadata(self, metadata, tmp_path):
        chunker = DocumentChunker(max_chars=100, overlap_chars=20)
        doc = tmp_path / "secao_longa.txt"
        texto_longo = (
            "Art. 15 O estudante poderá trancar a matrícula em até dois semestres consecutivos. "
            "Para tanto, deverá abrir requerimento junto à Secretaria Acadêmica apresentando "
            "justificativa formal e comprovante de quitação financeira."
        )
        doc.write_text(texto_longo, encoding="utf-8")

        chunks = chunker.chunk_document(doc, metadata)
        assert len(chunks) >= 2  # Texto dividido em múltiplos chunks pequenos
        for chunk in chunks:
            assert "parent_text" in chunk.metadata
            assert "parent_section" in chunk.metadata
            # O parent_text contém o texto completo da seção pai
            assert chunk.metadata["parent_section"] == "Art. 15"
            assert "justificativa formal" in chunk.metadata["parent_text"]

    def test_secao_acima_do_orcamento_nao_duplica_parent_text(self, metadata, tmp_path):
        """Uma página sem estrutura jurídica não pode clonar 329 KB em cada chunk."""
        chunker = DocumentChunker(max_chars=300, overlap_chars=50, parent_max_chars=1000)
        doc = tmp_path / "guia_flat.txt"
        item = "Item do guia do servidor com explicacao razoavelmente longa sobre o servico. "
        doc.write_text(item * 40, encoding="utf-8")  # ~2600 chars em uma única seção

        chunks = chunker.chunk_document(doc, metadata)
        assert len(chunks) >= 3
        for chunk in chunks:
            assert chunk.metadata["parent_text"] is None
            assert chunk.metadata["parent_section"] == "documento"
            assert len(chunk.text) <= chunker.max_chars + len("Este trecho pertence") + 200


class TestAncoragemEmSentenca:
    """Chunk não pode iniciar no meio de palavra/frase (bug dos fragmentos da LDB)."""

    def test_nenhum_chunk_comeca_no_meio_de_palavra(self):
        chunker = DocumentChunker(max_chars=600, overlap_chars=120)
        # Reproduz o padrão de extração HTML/PDF: quebras de linha "soft" no
        # meio da frase; o chunker antigo cortava na última \n e o overlap não
        # ancorado gerava chunks como "senvolvimento do processo..." e "la Lei...".
        sent1 = (
            "O ensino religioso, católico e evangélico, constitui disciplina dos horários normais "
            "das escolas públicas de ensino fundamental, assegurando o respeito à diversidade "
            "cultural e religiosa."
        )
        sent2 = (
            "Os currículos do ensino fundamental e médio devem ter uma base nacional comum, a ser "
            "complementada, em cada sistema de ensino e estabelecimento escolar, por uma parte "
            "diversificada, exigida pelas características regionais e locais da sociedade, da "
            "cultura, da economia e do educando."
        )
        sent3 = (
            "A educação básica em todos os níveis será marcada por uma gestão democrática, "
            "assegurando a participação dos profissionais da educação na elaboração do projeto "
            "pedagógico e das comunidades escolar e local em conselhos escolares ou equivalentes."
        )
        text = sent1 + "\n" + sent2[:80] + "\n" + sent2[80:] + "\n" + sent3[:50] + "\n" + sent3[50:]
        parts = chunker._split_text(text)
        assert len(parts) >= 2
        for p in parts:
            assert re.match(r"[A-ZÀ-Ü0-9§]", p), f"chunk inicia no meio da frase: {p[:40]!r}"

    def test_overlap_ancorado_no_comeco_de_sentenca(self):
        chunker = DocumentChunker(max_chars=110, overlap_chars=60)
        text = (
            "Primeira sentença tem cinquenta e um caracteres no total. "
            "Segunda sentença tem quarenta e seis caracteres, sim. "
            "Terceira sentença completa possui cinquenta caracteres."
        )
        parts = chunker._split_text(text)
        assert len(parts) >= 2
        for p in parts:
            assert re.match(r"[A-ZÀ-Ü0-9§]", p), f"overlap iniciou no meio da frase: {p[:30]!r}"
        assert sum(len(p) for p in parts) > len(text)  # overlap não foi eliminado

    def test_hard_split_de_unidade_gigante_nao_rasga_palavra(self):
        chunker = DocumentChunker(max_chars=100, overlap_chars=10)
        text = " ".join(["palavra"] * 60)  # ~420 chars, sem pontuação nem quebras
        parts = chunker._split_text(text)
        assert len(parts) >= 4
        for p in parts:
            for token in p.split():
                assert token == "palavra"

    def test_paragrafo_enorme_com_quebras_soft_divide_em_limites_de_palavra(self):
        """Frase única de 900 chars com quebras soft: corte apenas em palavras."""
        chunker = DocumentChunker(max_chars=200, overlap_chars=40)
        frase = (
            "Art. 4º O acesso ao ensino fundamental é direito público subjetivo, podendo qualquer "
            "cidadão, grupo de cidadãos, associação comunitária, organização sindical, entidade de "
            "classe ou outra legalmente constituída, bem como o Ministério Público, fiscalizar o "
            "cumprimento desta obrigação, impondo-se ao Poder Público de ensino a obrigação de "
            "notificar o estabelecimento de ensino que não assegure a matrícula obrigatória, sob "
            "pena de multa e das demais sanções administrativas previstas nesta Lei, garantido o "
            "direito de defesa do notificado e o contraditório em procedimento próprio instaurado "
            "pela autoridade competente do sistema de ensino ao qual estiver vinculado o ente."
        )
        assert len(frase) > 600
        tokens = frase.split(" ")
        # Wrap "soft" realista: a quebra ocupa o lugar do espaço, nunca rasga palavra.
        text = "\n".join(" ".join(tokens[i : i + 8]) for i in range(0, len(tokens), 8))
        parts = chunker._split_text(text)
        assert len(parts) >= 3
        for p in parts:
            for token in p.split():
                assert token in set(frase.split()), f"fragmento de palavra: {token!r}"

    def test_corpus_ldb_real_nao_gera_inicio_meio_palavra(self):
        pytest.importorskip("trafilatura")
        kb = Path(__file__).resolve().parents[2] / "knowledge_base"
        ldb = kb / "ldb_9394_96.html"
        if not ldb.exists():
            pytest.skip("arquivo da LDB não baixado na knowledge_base")
        chunker = DocumentChunker(max_chars=3200, overlap_chars=480, contextualize=False)
        metadata = DocumentMetadata(
            instituicao="MEC",
            documento="LDB",
            publico_alvo="student",
            url_fonte="https://www.planalto.gov.br/ccivil_03/leis/l9394.htm",
        )
        chunks = chunker.chunk_document(ldb, metadata)
        assert len(chunks) >= 2
        for c in chunks:
            assert not re.match(r"[a-zà-ü]", c.text), (
                f"chunk {c.metadata['secao']} começa no meio da palavra: {c.text[:40]!r}"
            )
