"""Endpoint de chat da API.

Conforme doc 09 seção 2 — processa mensagens usando o grafo LangGraph.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage

from src.api.auth import get_current_user
from src.api.chat_common import build_initial_state, build_run_config
from src.api.schemas import (
    ChatHistoryMessage,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
)
from src.observability.logging import TRACE_ID_CTX_KEY, generate_trace_id
from src.rag.models import Source

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Cache do grafo (inicializado na inicialização da app)
_graph: CompiledStateGraph | None = None


def init_graph(graph: CompiledStateGraph) -> None:
    """Inicializa o grafo singleton para o módulo de chat."""
    global _graph
    _graph = graph


@router.post(
    "",
    response_model=ChatResponse,
    responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    """Processa uma mensagem do chat.

    Recebe a mensagem do usuário, invoca o grafo LangGraph de orquestração
    e retorna a resposta consolidada com fontes e agentes envolvidos.
    """
    if _graph is None:
        raise HTTPException(
            status_code=500,
            detail="Grafo não inicializado. Configure a aplicação antes de usar o chat.",
        )

    # Prepara o estado inicial
    trace_id = generate_trace_id()

    logger.info(
        "Chat request received",
        extra={
            TRACE_ID_CTX_KEY: trace_id,
            "profile": current_user["profile"],
            "user": current_user["email"],
            "session_id": request.session_id,
            "message_length": len(request.message),
        },
    )

    state = build_initial_state(current_user, request.message)

    # Configuração para o grafo
    # run_id fixo: o LangSmith adota esse UUID como id do trace, permitindo
    # anexar feedback humano (👍/👎) à execução correspondente.
    run_id = uuid.uuid4()
    config = build_run_config(current_user, request.session_id, run_id)

    try:
        result = await _graph.ainvoke(state, config)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar mensagem: {exc}",
        )

    # Extrai resposta
    last_message = result.get("messages", [])
    answer = last_message[-1].content if last_message else ""

    # Agentes envolvidos
    agents_involved = list(result.get("agent_results", {}).keys())

    # Fontes
    sources_raw = result.get("retrieved_sources", [])
    sources = [Source(**s) if isinstance(s, dict) else s for s in sources_raw]

    # Intenção
    decision = result.get("supervisor_decision", {})
    intent = decision.get("intent", "fora_de_escopo") if decision else "fora_de_escopo"

    return ChatResponse(
        session_id=request.session_id,
        message_id=str(run_id),
        answer=answer,
        agents_involved=agents_involved,
        sources=sources,
        intent=intent,
    )


@router.get(
    "/history",
    response_model=ChatHistoryResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def chat_history(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> ChatHistoryResponse:
    """Retorna as mensagens persistidas de uma sessão (T7.4 / RF2-04, RF2-05).

    Lê o estado da thread no checkpointer do grafo. A posse é validada pelo
    campo `user_id` do estado (gravado a cada escrita no `/chat`); sessões
    legadas sem associação são legíveis e associadas na próxima escrita.
    Agentes/fontes são omitidos no histórico — apenas o texto (documentado).
    """
    if _graph is None:
        raise HTTPException(
            status_code=500,
            detail="Grafo não inicializado. Configure a aplicação antes de usar o chat.",
        )

    config = {"configurable": {"thread_id": session_id}}
    snapshot = await _graph.aget_state(config)
    values = getattr(snapshot, "values", None) or {}
    state_messages = values.get("messages") or []
    if not state_messages:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    owner = values.get("user_id")
    if owner is not None and owner != current_user["email"]:
        raise HTTPException(status_code=403, detail="Sessão pertence a outro usuário")

    messages = [
        ChatHistoryMessage(
            role="user" if isinstance(m, HumanMessage) else "assistant",
            content=m.content,
        )
        for m in state_messages
    ]

    logger.info(
        "Chat history served",
        extra={"session_id": session_id, "user": current_user["email"], "count": len(messages)},
    )

    return ChatHistoryResponse(session_id=session_id, messages=messages)
