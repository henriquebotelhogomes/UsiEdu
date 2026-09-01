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

# Fronteiras de unidade de chunking: fim de sentença, parágrafo e marcadores
# jurídicos. Quebras de linha "soft" (wrap visual da página extraída) NÃO são
# fronteiras — foram elas que geraram chunks iniciando em "senvolvimento…".
_UNIT_DELIM_RE = re.compile(
    r"(?<=[.!?…])\s+"                            # fim de sentença
    r"|\n[ \t]*\n"                               # quebra de parágrafo
    r"|(?=(?:Art\.|§|T[ÍI]TULO|CAP[ÍI]TULO|SE[ÇC][ÃA]O)\s)"  # marcador jurídico
)


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
        contextualize: bool = True,
        parent_max_chars: int = 12000,
    ) -> None:
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.contextualize = contextualize
        self.parent_max_chars = parent_max_chars

    def chunk_document(
        self,
        file_path: Path,
        metadata: DocumentMetadata,
    ) -> list[Chunk]:
        """Extrai texto de um arquivo e retorna chunks com metadados e contextualização."""
        text = self._extract_text(file_path)
        if not text.strip():
            return []

        sections = self._detect_sections(text)
        chunks: list[Chunk] = []
        chunk_index = 0

        for section_name, section_text in sections:
            parts = self._split_text(section_text)
            parent_text = (
                section_text if len(section_text) <= self.parent_max_chars else None
            )
            context_prefix = (
                self._build_context_prefix(metadata, section_name)
                if self.contextualize
                else ""
            )
            for part in parts:
                chunk_id = self._make_chunk_id(metadata, chunk_index)
                final_text = f"{context_prefix}{part}" if context_prefix else part
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        text=final_text,
                        metadata={
                            "instituicao": metadata.instituicao,
                            "documento": metadata.documento,
                            "secao": section_name,
                            "pagina": None,
                            "url_fonte": metadata.url_fonte,
                            "publico_alvo": metadata.publico_alvo,
                            "chunk_index": chunk_index,
                            "original_text": part,
                            "parent_text": parent_text,
                            "parent_section": section_name,
                        },
                    )
                )
                chunk_index += 1

        return chunks

    @staticmethod
    def _build_context_prefix(metadata: DocumentMetadata, section_name: str) -> str:
        """Gera o prefixo de contextualização (padrão Anthropic Contextual Retrieval)."""
        prefix = f"Este trecho pertence ao documento '{metadata.documento}'"
        if metadata.instituicao:
            prefix += f" da instituição '{metadata.instituicao}'"
        if section_name and section_name not in ("documento", "preâmbulo"):
            prefix += f", seção '{section_name}'"
        elif section_name == "preâmbulo":
            prefix += ", preâmbulo introdutório"
        prefix += ".\n\n"
        return prefix

    def _extract_text(self, file_path: Path) -> str:
        """Extrai texto de PDF ou HTML."""
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            return self._extract_pdf(file_path)
        elif suffix in (".html", ".htm"):
            return self._extract_html(file_path)
        else:
            try:
                return file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return file_path.read_text(encoding="latin-1")

    @staticmethod
    def _extract_pdf(file_path: Path) -> str:
        """Extrai texto de PDF usando PyMuPDF, preservando tabelas."""
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        try:
            fitz.TOOLS.mupdf_display_errors(False)
        except Exception:
            pass

        parts: list[str] = []
        try:
            with fitz.open(str(file_path)) as doc:
                for page in doc:
                    try:
                        txt = page.get_text()
                        if txt and txt.strip():
                            parts.append(txt)
                    except Exception:
                        pass
        except Exception:
            pass

        return "\n".join(parts)

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
        """Divide texto em chunks ancorados em fronteiras de sentença/parágrafo.

        Unidades de texto são agrupadas até `max_chars`; o overlap carrega
        unidades inteiras do chunk anterior, então nenhum chunk começa no
        meio de uma palavra. Unidades maiores que o limite (texto sem
        pontuação) são divididas em fronteiras de palavra.
        """
        stripped = text.strip()
        if not stripped:
            return []
        if len(stripped) <= self.max_chars:
            return [stripped]

        units = self._unit_spans(stripped)
        parts: list[str] = []
        i = 0
        n = len(units)

        while i < n:
            j, length = i, 0
            while j < n:
                unit_len = self._span_len(stripped, units[j])
                added = unit_len if j == i else unit_len + 1
                if length + added > self.max_chars:
                    break
                length += added
                j += 1

            if j == i:  # unidade sozinha não cabe no chunk: corte por palavra
                for lo, hi in self._hard_split(stripped, units[i][0], units[i][1]):
                    part = stripped[lo:hi].strip()
                    if part:
                        parts.append(part)
                i += 1
                continue

            parts.append(stripped[units[i][0] : units[j - 1][1]].strip())

            carry, used, k = 0, 0, 1
            while k < j - i:  # nunca carregar o chunk inteiro
                candidate = self._span_len(stripped, units[j - 1 - k])
                if used + candidate + (1 if carry else 0) > self.overlap_chars:
                    break
                used += candidate + (1 if carry else 0)
                carry += 1
                k += 1

            i = j - carry if carry else j

        return [p for p in parts if p]

    @staticmethod
    def _span_len(text: str, span: tuple[int, int]) -> int:
        return len(text[span[0] : span[1]].strip())

    @staticmethod
    def _unit_spans(text: str) -> list[tuple[int, int]]:
        """Retorna os intervalos das unidades (sentenças/parágrafos/marcadores) do texto."""
        cuts = [0]
        for match in _UNIT_DELIM_RE.finditer(text):
            if match.end() > cuts[-1]:
                cuts.append(match.end())
        cuts.append(len(text))
        return [(lo, hi) for lo, hi in zip(cuts, cuts[1:]) if text[lo:hi].strip()]

    def _hard_split(self, text: str, lo: int, hi: int) -> list[tuple[int, int]]:
        """Divide uma unidade maior que o limite, cortando no último espaço do recorte."""
        spans: list[tuple[int, int]] = []
        pos = lo
        while hi - pos > self.max_chars:
            limit = pos + self.max_chars
            cut = text.rfind(" ", pos + 1, limit)
            if cut <= pos:
                cut = text.rfind("\n", pos + 1, limit)
            if cut <= pos:
                cut = limit  # sequência sem espaços: único caso de corte intra-palavra
            spans.append((pos, cut))
            pos = cut
        if pos < hi:
            spans.append((pos, hi))
        return spans

    @staticmethod
    def _make_chunk_id(metadata: DocumentMetadata, index: int) -> str:
        """Gera ID determinístico para o chunk (usado para idempotência)."""
        import hashlib

        key = f"{metadata.instituicao}:{metadata.documento}:{index}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]
