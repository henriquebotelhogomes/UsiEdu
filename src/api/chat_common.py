"""Lógica comum dos endpoints de chat (T7.3).

Centraliza a construção do estado inicial do grafo e do `RunnableConfig`
(com `run_id` adotado pelo LangSmith como id do trace), compartilhados
entre `POST /chat` e `POST /chat/stream`.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

# T9.2 — política de cache: apenas intenções cujo resultado vem só da base
# de conhecimento (sem dados pessoais de tools).
INTENTS_CACHEAVEIS = {"institucional"}


def build_initial_state(current_user: dict, message: str) -> dict:
    """Prepara o estado inicial do grafo para uma mensagem de chat."""
    return {
        "user_id": current_user["email"],
        "profile": current_user["profile"],
        "messages": [HumanMessage(content=message)],
        "plan": None,
        "delegations": [],
        "agent_results": {},
        "retrieved_sources": [],
        "needs_more_info": False,
        "cycle_count": 0,
        "supervisor_decision": None,
    }


def build_run_config(current_user: dict, session_id: str, run_id: uuid.UUID) -> dict:
    """Monta o `RunnableConfig` da execução do grafo.

    O `run_id` é adotado pelo LangSmith como id do trace, permitindo anexar
    feedback humano (👍/👎) à execução; o `message_id` retornado ao cliente é
    o mesmo valor.
    """
    return {
        "run_id": run_id,
        "metadata": {
            "telemetry_scope": "demo_minimized",
        },
        "configurable": {
            "thread_id": session_id,
        },
    }


async def sessao_sem_historico(graph: CompiledStateGraph, session_id: str) -> bool:
    """True se a sessão não tem mensagens prévias (T9.2).

    O cache vale apenas para a primeira mensagem da sessão. Sem checkpointer
    (grafo de teste), não existe contexto prévio persistente → True.
    """
    try:
        snapshot = await graph.aget_state({"configurable": {"thread_id": session_id}})
        values = getattr(snapshot, "values", None) or {}
        return not values.get("messages")
    except Exception:  # noqa: BLE001 — sem checkpointer configurado
        return True


def resposta_cacheavel(intent: str | None, primeira_mensagem: bool) -> bool:
    """Política de gravação no cache (T9.2): 1ª mensagem + intenção cacheável."""
    return primeira_mensagem and intent in INTENTS_CACHEAVEIS


def payload_para_cache(answer: str, agents: list[str], sources: list, intent: str) -> dict:
    """Resposta serializável para o cache (fontes originais, contrato completo)."""
    return {
        "answer": answer,
        "agents": agents,
        "sources": [s.model_dump() if hasattr(s, "model_dump") else dict(s) for s in sources],
        "intent": intent,
    }
