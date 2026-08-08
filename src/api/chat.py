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
from src.api.schemas import ChatRequest, ChatResponse, ErrorResponse
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

    state = {
        "user_id": current_user["email"],
        "profile": current_user["profile"],
        "messages": [HumanMessage(content=request.message)],
        "plan": None,
        "delegations": [],
        "agent_results": {},
        "retrieved_sources": [],
        "needs_more_info": False,
        "cycle_count": 0,
        "supervisor_decision": None,
    }

    # Configuração para o grafo
    # run_id fixo: o LangSmith adota esse UUID como id do trace, permitindo
    # anexar feedback humano (👍/👎) à execução correspondente.
    run_id = uuid.uuid4()
    config = {
        "run_id": run_id,
        "metadata": {"message_id": str(run_id), "session_id": request.session_id},
        "configurable": {
            "thread_id": request.session_id,
        },
    }

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
