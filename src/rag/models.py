"""Modelos de dados compartilhados para o pipeline de RAG."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Metadados de um documento-fonte na base de conhecimento."""

    instituicao: str
    documento: str
    publico_alvo: str  # "student" | "staff" | "both"
    url_fonte: str = ""
    file_type: str = ""  # "pdf" | "html"


class Chunk(BaseModel):
    """Um chunk de texto com metadados completos."""

    id: str
    text: str
    metadata: dict


class Source(BaseModel):
    """Fonte citada em uma resposta (contrato da API — doc 09 seção 2)."""

    document: str = Field(description="Nome do documento, ex.: 'Regimento Geral da UnB'")
    section: str | None = Field(None, description="Seção, ex.: 'Título III, Cap. II, Art. 112'")
    excerpt: str = Field(description="Trecho recuperado")
    url: str | None = None


class RetrievalResult(BaseModel):
    """Resultado de uma busca no retriever."""

    text: str
    score: float
    source: Source
