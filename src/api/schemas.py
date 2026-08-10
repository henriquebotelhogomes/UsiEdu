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
    message_id: str = Field(..., description="ID da resposta (run_id do trace para feedback)")
    answer: str = Field(..., description="Resposta do assistente")
    agents_involved: list[str] = Field(default_factory=list, description="Agentes que participaram")
    sources: list[Source] = Field(default_factory=list, description="Fontes consultadas")
    intent: Literal["academico", "financeiro", "institucional", "composta", "fora_de_escopo"] = (
        Field(..., description="Intenção classificada pelo supervisor")
    )
    from_cache: bool = Field(
        False, description="True quando a resposta veio do cache semântico (T9.2)"
    )


class ChatHistoryMessage(BaseModel):
    """Mensagem persistida de uma sessão (T7.4 / RF2-05)."""

    role: Literal["user", "assistant"] = Field(..., description="Autor da mensagem")
    content: str = Field(..., description="Conteúdo textual da mensagem")
    timestamp: str | None = Field(
        default=None,
        description="Timestamp da mensagem (o checkpointer não persiste; nulo)",
    )


class ChatHistoryResponse(BaseModel):
    """Histórico de mensagens persistidas de uma sessão (T7.4 / RF2-05)."""

    session_id: str = Field(..., description="ID da sessão (thread_id)")
    messages: list[ChatHistoryMessage] = Field(
        default_factory=list, description="Mensagens na ordem da conversa"
    )


class FeedbackRequest(BaseModel):
    """Feedback humano (human-on-the-loop) sobre uma resposta do chat."""

    session_id: str = Field(..., description="ID da sessão da mensagem avaliada")
    message_id: str = Field(..., description="ID da resposta avaliada (run_id do trace)")
    rating: Literal["up", "down"] = Field(
        ..., description="Polegar para cima (up) ou para baixo (down)"
    )
    comment: str | None = Field(default=None, max_length=500, description="Comentário opcional")


class FeedbackResponse(BaseModel):
    """Confirmação de registro de feedback."""

    status: str = Field(default="ok", description="Status do registro")
    feedback_id: int = Field(..., description="ID do feedback registrado")


class FeedbackStats(BaseModel):
    """Métricas agregadas de feedback."""

    total: int = Field(..., description="Total de feedbacks")
    up: int = Field(..., description="Respostas avaliadas positivamente")
    down: int = Field(..., description="Respostas avaliadas negativamente")
    satisfaction: float = Field(..., description="Taxa de satisfação (0–1)")


class FeedbackRecentItem(BaseModel):
    """Item da lista de feedbacks recentes (T8.2)."""

    rating: Literal["up", "down"] = Field(..., description="Avaliação registrada")
    comment: str | None = Field(default=None, description="Comentário opcional do usuário")
    profile: str = Field(..., description="Perfil de quem avaliou (student/staff)")
    created_at: str = Field(..., description="Data/hora do registro (ISO 8601)")
    message_ref: str = Field(
        ..., description="Hash truncado do message_id (não expõe o UUID do run)"
    )


class FeedbackRecentResponse(BaseModel):
    """Lista dos feedbacks mais recentes (T8.2 — página /insights)."""

    items: list[FeedbackRecentItem] = Field(..., description="Feedbacks mais recentes primeiro")


class ErrorResponse(BaseModel):
    """Resposta de erro padrão."""

    detail: str = Field(..., description="Descrição do erro")
    error_code: str | None = Field(default=None, description="Código interno do erro")
