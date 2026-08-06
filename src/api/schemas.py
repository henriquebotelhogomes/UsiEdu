"""Schemas Pydantic da API REST.

Conforme doc 09 seção 2 — contratos de entrada e saída.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.rag.models import Source


class LoginRequest(BaseModel):
    """Payload de login do usuário."""

    email: str = Field(..., description="E-mail institucional do usuário")
    password: str = Field(..., description="Senha do usuário")


class LoginResponse(BaseModel):
    """Resposta de login bem-sucedido."""

    access_token: str = Field(..., description="JWT de acesso")
    token_type: str = Field(default="bearer", description="Tipo do token")
    profile: Literal["student", "staff"] = Field(..., description="Perfil do usuário")
    display_name: str = Field(..., description="Nome de exibição do usuário")


class ChatRequest(BaseModel):
    """Payload de uma mensagem no chat."""

    session_id: str = Field(..., description="ID da sessão (thread_id do checkpointer)")
    message: str = Field(..., min_length=1, max_length=2000, description="Mensagem do usuário")


class ChatResponse(BaseModel):
    """Resposta do chat."""

    session_id: str = Field(..., description="ID da sessão")
    answer: str = Field(..., description="Resposta do assistente")
    agents_involved: list[str] = Field(default_factory=list, description="Agentes que participaram")
    sources: list[Source] = Field(default_factory=list, description="Fontes consultadas")
    intent: Literal["academico", "financeiro", "institucional", "composta", "fora_de_escopo"] = (
        Field(..., description="Intenção classificada pelo supervisor")
    )


class ErrorResponse(BaseModel):
    """Resposta de erro padrão."""

    detail: str = Field(..., description="Descrição do erro")
    error_code: str | None = Field(default=None, description="Código interno do erro")
