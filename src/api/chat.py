"""Endpoint de chat da API.

Conforme doc 09 seção 2 e PRDs v3/v4 — processa mensagens usando o grafo LangGraph.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from langchain_core.messages import AIMessage, HumanMessage

from src.api.auth import get_current_user
from src.api.chat_common import (
    build_initial_state,
    build_run_config,
    payload_para_cache,
    resposta_cacheavel,
    sessao_sem_historico,
)
from src.api.rate_limit import LIMITE_CHAT, limiter
from src.api.schemas import (
    ChatHistoryMessage,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    ResumeRequest,
)
from src.observability.logging import TRACE_ID_CTX_KEY, generate_trace_id
from src.rag.cache import get_chat_cache
from src.rag.models import Source
from src.security.guardrails import (
    RESPOSTA_SEGURA_PADRAO,
    detect_injection,
    log_guardrail,
    mask_pii,
    registrar_guardrail_langsmith,
    validate_answer,
)

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
    responses={
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(LIMITE_CHAT)
async def chat(
    request: Request,
    payload: ChatRequest,
    response: Response,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    """Processa uma mensagem do chat."""
    if _graph is None:
        raise HTTPException(
            status_code=500,
            detail="Grafo não inicializado. Configure a aplicação antes de usar o chat.",
        )

    trace_id = generate_trace_id()

    # Sanitização PII (RF4-03)
    sanitized_message, pii_detected = mask_pii(payload.message)

    logger.info(
        "Chat request received",
        extra={
            TRACE_ID_CTX_KEY: trace_id,
            "profile": current_user["profile"],
            "user": current_user["email"],
            "session_id": payload.session_id,
            "message_length": len(payload.message),
            "pii_detected": pii_detected,
        },
    )

    primeira_mensagem = await sessao_sem_historico(_graph, payload.session_id)
    cache = get_chat_cache()

    if primeira_mensagem:
        cached = await cache.lookup(current_user["profile"], payload.message)
        if cached:
            cached_data = cached["answer"]
            return ChatResponse(
                session_id=payload.session_id,
                message_id=str(uuid.uuid4()),
                answer=cached_data["answer"],
                agents_involved=cached_data.get("agents", ["institucional"]),
                sources=[
                    Source(**s) if isinstance(s, dict) else s
                    for s in cached_data.get("sources", [])
                ],
                intent=cached_data.get("intent", "institucional"),
                from_cache=True,
            )

    injections = detect_injection(payload.message)
    if injections:
        logger.warning(
            "Suspected injection pattern in user query",
            extra={"injections": injections, "session_id": payload.session_id},
        )

    run_id = uuid.uuid4()
    run_config = build_run_config(current_user, payload.session_id, run_id)
    initial_state = build_initial_state(current_user, sanitized_message)

    try:
        final_state = await _graph.ainvoke(initial_state, run_config)
    except Exception as exc:
        logger.exception(
            "Graph execution failed",
            extra={
                TRACE_ID_CTX_KEY: trace_id,
                "session_id": payload.session_id,
                "user": current_user["email"],
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Erro ao processar mensagem no grafo de agentes.",
        ) from exc

    # Extrai resposta do último AIMessage (se pausado por HITL, usa resposta intermediária)
    final_messages = final_state.get("messages", [])
    ai_messages = [m for m in final_messages if isinstance(m, AIMessage)]
    if ai_messages:
        raw_answer = ai_messages[-1].content
    else:
        raw_answer = "Processamento iniciado. Aguardando aprovação para prosseguir."

    agent_results = final_state.get("agent_results", {})
    agents_involved = list(agent_results.keys()) if agent_results else ["supervisor"]
    raw_sources = final_state.get("retrieved_sources", [])
    sources = [
        s if isinstance(s, Source) else Source(**s) for s in raw_sources
    ]

    decision = final_state.get("supervisor_decision")
    if hasattr(decision, "intent"):
        intent = decision.intent
    elif isinstance(decision, dict):
        intent = decision.get("intent", "academico")
    else:
        intent = "academico"

    if intent not in ("academico", "financeiro", "institucional", "composta", "fora_de_escopo"):
        intent = "academico"

    # Guardrail de saída
    guardrail_result = validate_answer(raw_answer)
    guardrail_disparado = not guardrail_result.safe

    if guardrail_disparado:
        answer = RESPOSTA_SEGURA_PADRAO
        log_guardrail(
            run_id,
            guardrail_result.reasons,
            origem="endpoint_chat",
            session_id=payload.session_id,
            user=current_user["email"],
        )
        registrar_guardrail_langsmith(run_id, guardrail_result.reasons)
    else:
        answer = raw_answer

    if resposta_cacheavel(intent, primeira_mensagem) and not guardrail_disparado:
        await cache.store(
            current_user["profile"],
            payload.message,
            payload_para_cache(answer, agents_involved, sources, intent),
        )

    return ChatResponse(
        session_id=payload.session_id,
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
    """Retorna as mensagens persistidas de uma sessão."""
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


@router.post(
    "/resume",
    response_model=ChatResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def chat_resume(
    payload: ResumeRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    """Retoma a execução de uma sessão que foi pausada por Human-in-the-Loop (RF4-01, RF4-02)."""
    if _graph is None:
        raise HTTPException(
            status_code=500,
            detail="Grafo não inicializado. Configure a aplicação antes de usar o chat.",
        )

    config = {"configurable": {"thread_id": payload.session_id}}
    snapshot = await _graph.aget_state(config)
    values = getattr(snapshot, "values", None) or {}

    if not values.get("messages"):
        raise HTTPException(status_code=404, detail="Sessão não encontrada para retomada")

    owner = values.get("user_id")
    if owner is not None and owner != current_user["email"]:
        raise HTTPException(status_code=403, detail="Sessão pertence a outro usuário")

    if payload.user_input:
        await _graph.aupdate_state(
            config, {"messages": [HumanMessage(content=payload.user_input)]}
        )

    run_id = uuid.uuid4()
    run_config = build_run_config(current_user, payload.session_id, run_id)

    final_state = await _graph.ainvoke(None, run_config)

    final_messages = final_state.get("messages", [])
    ai_messages = [m for m in final_messages if isinstance(m, AIMessage)]
    answer = ai_messages[-1].content if ai_messages else "Execução concluída com sucesso."
    agent_results = final_state.get("agent_results", {})
    agents_involved = list(agent_results.keys()) if agent_results else ["supervisor"]
    raw_sources = final_state.get("retrieved_sources", [])
    sources = [
        s if isinstance(s, Source) else Source(**s) for s in raw_sources
    ]
    decision = final_state.get("supervisor_decision")
    if hasattr(decision, "intent"):
        intent = decision.intent
    elif isinstance(decision, dict):
        intent = decision.get("intent", "academico")
    else:
        intent = "academico"

    if intent not in ("academico", "financeiro", "institucional", "composta", "fora_de_escopo"):
        intent = "academico"

    return ChatResponse(
        session_id=payload.session_id,
        message_id=str(run_id),
        answer=answer,
        agents_involved=agents_involved,
        sources=sources,
        intent=intent,
    )
