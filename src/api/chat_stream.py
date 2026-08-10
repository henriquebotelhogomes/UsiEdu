"""Endpoint de streaming SSE do chat (T7.3 — RF2-03).

`POST /chat/stream` executa o grafo com `astream_events(version="v2")` e
envia ao cliente eventos SSE (`data: {json}\n\n`):

- `meta`: `{session_id, message_id}` — início (mesmo `run_id` do LangSmith);
- `token`: `{delta}` — cada chunk do LLM dos agentes de resposta final
  (tokens do supervisor — JSON de classificação — nunca são streamados);
- `final`: `{agents, sources, usage, answer}` — ao término do grafo;
- `error`: `{detail}` — qualquer exceção (fecha o stream).

O `POST /chat` tradicional permanece como fallback obrigatório.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.api import chat as chat_module
from src.api.auth import get_current_user
from src.api.chat_common import (
    build_initial_state,
    build_run_config,
    payload_para_cache,
    resposta_cacheavel,
    sessao_sem_historico,
)
from src.api.rate_limit import LIMITE_CHAT, limiter
from src.api.schemas import ChatRequest, ErrorResponse
from src.rag.cache import get_chat_cache
from src.rag.models import Source

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Nós cujos tokens de LLM fazem parte da resposta final (T7.3). O supervisor
# (classificação de intenção em JSON) é sempre excluído do stream.
STREAMABLE_NODES = {"academico", "financeiro", "documental"}


def _sse(payload: dict) -> str:
    """Serializa um evento SSE como linha única `data: {json}\n\n`."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post(
    "/stream",
    responses={
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(LIMITE_CHAT)
async def chat_stream(
    request: Request,
    payload: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Processa uma mensagem e streama a resposta via SSE.

    O `message_id` enviado em `meta` é o `run_id` do trace no LangSmith —
    o mesmo usado no endpoint de feedback. Limitado por usuário (T9.1);
    o parâmetro `request` é o starlette Request exigido pelo slowapi.
    """
    graph = chat_module._graph
    if graph is None:
        raise HTTPException(
            status_code=500,
            detail="Grafo não inicializado. Configure a aplicação antes de usar o chat.",
        )

    run_id = uuid.uuid4()
    state = build_initial_state(current_user, payload.message)
    config = build_run_config(current_user, payload.session_id, run_id)

    logger.info(
        "Chat stream request received",
        extra={
            "profile": current_user["profile"],
            "user": current_user["email"],
            "session_id": payload.session_id,
            "message_length": len(payload.message),
        },
    )

    # Cache semântico (T9.2): hit dispensa o grafo; stream sintético com o
    # mesmo contrato (meta → token → final com from_cache)
    cache = get_chat_cache()
    primeira_mensagem = await sessao_sem_historico(graph, payload.session_id)
    hit = (
        await cache.lookup(current_user["profile"], payload.message) if primeira_mensagem else None
    )
    if hit:
        cached = hit["answer"]

        async def cached_stream() -> AsyncIterator[str]:
            yield _sse(
                {"event": "meta", "session_id": payload.session_id, "message_id": str(run_id)}
            )
            yield _sse({"event": "token", "delta": cached["answer"]})
            yield _sse(
                {
                    "event": "final",
                    "agents": cached.get("agents", []),
                    "sources": cached.get("sources", []),
                    "usage": {"intent": cached.get("intent", "institucional")},
                    "answer": cached["answer"],
                    "from_cache": True,
                }
            )

        logger.info(
            "Chat stream served from cache",
            extra={"session_id": payload.session_id, "exact": hit["exact"], "cache_hit": True},
        )
        return StreamingResponse(
            cached_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    async def event_stream() -> AsyncIterator[str]:
        yield _sse({"event": "meta", "session_id": payload.session_id, "message_id": str(run_id)})
        try:
            async for event in graph.astream_events(state, config, version="v2"):
                if event["event"] != "on_chat_model_stream":
                    continue
                node = (event.get("metadata") or {}).get("langgraph_node")
                if node not in STREAMABLE_NODES:
                    continue
                delta = getattr(event["data"].get("chunk"), "content", "")
                if isinstance(delta, str) and delta:
                    yield _sse({"event": "token", "delta": delta})

            # Estado final persistido no checkpointer (mesma thread do /chat)
            snapshot = await graph.aget_state(config)
            values = getattr(snapshot, "values", None) or {}
            messages = values.get("messages") or []
            answer = messages[-1].content if messages else ""
            agents = list(values.get("agent_results", {}).keys())
            sources = [
                Source(**s) if isinstance(s, dict) else s
                for s in values.get("retrieved_sources", [])
            ]
            decision = values.get("supervisor_decision") or {}
            intent = decision.get("intent", "fora_de_escopo")

            yield _sse(
                {
                    "event": "final",
                    "agents": agents,
                    "sources": [s.model_dump() for s in sources],
                    "usage": {"intent": intent},
                    # Campo extra além do contrato do PRD: permite ao cliente
                    # reconciliar o texto final (a consolidação pode adicionar
                    # sufixos que não passaram pelo stream de tokens).
                    "answer": answer if isinstance(answer, str) else str(answer),
                }
            )

            # Alimenta o cache (T9.2): 1ª mensagem + intenção cacheável
            if resposta_cacheavel(intent, primeira_mensagem):
                await cache.store(
                    current_user["profile"],
                    payload.message,
                    payload_para_cache(
                        answer if isinstance(answer, str) else str(answer),
                        agents,
                        sources,
                        intent,
                    ),
                )
        except asyncio.CancelledError:
            # Cliente desconectou — propaga para o FastAPI encerrar o stream.
            raise
        except Exception as exc:
            logger.exception("Chat stream error")
            yield _sse({"event": "error", "detail": f"Erro ao processar mensagem: {exc}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Impede buffering em proxies (nginx também exige proxy_buffering off)
            "X-Accel-Buffering": "no",
        },
    )
