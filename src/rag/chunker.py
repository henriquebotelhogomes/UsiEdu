"""Extração de texto e chunking semântico de documentos."""

from __future__ import annotations

import re
from pathlib import Path

from src.rag.models import Chunk, DocumentMetadata

# Padrões de cabeçalhos em documentos jurídicos brasileiros
_SECTION_PATTERNS = [
    r"(?:^|\n)(TÍTULO\s+[IVXLCDM]+)",
    r"(?:^|\n)(CAPÍTULO\s+[IVXLCDM]+)",
    r"(?:^|\n)(SEÇÃO\s+[IVXLCDM]+)",
    r"(?:^|\n)(Art\.\s+\d+)",
]
_SECTION_RE = re.compile("|".join(_SECTION_PATTERNS), re.MULTILINE)


class DocumentChunker:
    """Divide documentos em chunks semânticos com overlap.

    Estratégia:
    1. Extrai texto do documento (PDF via PyMuPDF, HTML via trafilatura).
    2. Detecta seções por cabeçalhos (TÍTULO, CAPÍTULO, Art.).
    3. Seções grandes são subdivididas com overlap.
    4. Cada chunk recebe metadados completos para citação de fonte.
    """

    def __init__(
        self,
        max_chars: int = 3200,
        overlap_chars: int = 480,
    ) -> None:
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk_document(
        self,
        file_path: Path,
        metadata: DocumentMetadata,
    ) -> list[Chunk]:
        """Extrai texto de um arquivo e retorna chunks com metadados."""
        text = self._extract_text(file_path)
        if not text.strip():
            return []

        sections = self._detect_sections(text)
        chunks: list[Chunk] = []
        chunk_index = 0

        for section_name, section_text in sections:
            parts = self._split_text(section_text)
            for part in parts:
                chunk_id = self._make_chunk_id(metadata, chunk_index)
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        text=part,
                        metadata={
                            "instituicao": metadata.instituicao,
                            "documento": metadata.documento,
                            "secao": section_name,
                            "pagina": None,
                            "url_fonte": metadata.url_fonte,
                            "publico_alvo": metadata.publico_alvo,
                            "chunk_index": chunk_index,
                        },
                    )
                )
                chunk_index += 1

        return chunks

    def _extract_text(self, file_path: Path) -> str:
        """Extrai texto de PDF ou HTML."""
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            return self._extract_pdf(file_path)
        elif suffix in (".html", ".htm"):
            return self._extract_html(file_path)
        else:
            return file_path.read_text(encoding="utf-8")

    @staticmethod
    def _extract_pdf(file_path: Path) -> str:
        """Extrai texto de PDF usando PyMuPDF."""
        import fitz  # PyMuPDF

        doc = fitz.open(str(file_path))
        texts = []
        for page in doc:
            texts.append(page.get_text())
        doc.close()
        return "\n".join(texts)

    @staticmethod
    def _extract_html(file_path: Path) -> str:
        """Extrai texto de HTML usando trafilatura.

        Detecta o encoding do arquivo: tenta UTF-8 primeiro e cai
        para Latin-1 (ISO-8859-1), comum em páginas do Planalto.
        """
        import trafilatura

        raw = file_path.read_bytes()
        try:
            html = raw.decode("utf-8")
        except UnicodeDecodeError:
            html = raw.decode("latin-1")
        text = trafilatura.extract(html)
        return text or ""

    @staticmethod
    def _detect_sections(text: str) -> list[tuple[str, str]]:
        """Detecta seções em documentos jurídicos brasileiros.

        Retorna lista de (nome_da_seção, texto_da_seção).
        Se nenhuma seção for detectada, retorna o texto inteiro como uma seção.
        """
        matches = list(_SECTION_RE.finditer(text))

        if not matches:
            return [("documento", text)]

        sections: list[tuple[str, str]] = []

        # Texto antes da primeira seção
        if matches[0].start() > 0:
            prefix = text[: matches[0].start()].strip()
            if prefix:
                sections.append(("preâmbulo", prefix))

        for i, match in enumerate(matches):
            # Encontra o nome da seção (primeiro grupo não-None)
            section_name = next(
                (g for g in match.groups() if g is not None),
                "seção",
            )
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[start:end].strip()
            if section_text:
                sections.append((section_name, section_text))

        return sections

    def _split_text(self, text: str) -> list[str]:
        """Divide texto em pedaços com overlap, respeitando limites de sentenças."""
        if len(text) <= self.max_chars:
            return [text.strip()] if text.strip() else []

        parts: list[str] = []
        start = 0

        while start < len(text):
            end = start + self.max_chars

            if end >= len(text):
                parts.append(text[start:].strip())
                break

            # Tenta quebrar no final de uma sentença
            break_point = max(
                text.rfind(". ", start, end),
                text.rfind(".\n", start, end),
                text.rfind("\n\n", start, end),
                text.rfind("\n", start, end),
            )

            if break_point > start + self.max_chars // 2:
                end = break_point + 1

            part = text[start:end].strip()
            if part:
                parts.append(part)

            # Avança com overlap, garantindo progresso
            prev_start = start
            start = end - self.overlap_chars
            if start <= prev_start:
                start = end  # garante progresso se overlap não avançar

        return [p for p in parts if p]

    @staticmethod
    def _make_chunk_id(metadata: DocumentMetadata, index: int) -> str:
        """Gera ID determinístico para o chunk (usado para idempotência)."""
        import hashlib

        key = f"{metadata.instituicao}:{metadata.documento}:{index}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]
