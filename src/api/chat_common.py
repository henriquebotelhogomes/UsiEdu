"""Lógica comum dos endpoints de chat (T7.3 / PRD v3).

Centraliza a construção do estado inicial do grafo, do `RunnableConfig`
(com `run_id` adotado pelo LangSmith como id do trace), poda de mensagens
e validações compartilhadas entre `POST /chat` e `POST /chat/stream`.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from langchain_core.messages import AnyMessage, HumanMessage, trim_messages

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

# T9.2 — política de cache: apenas intenções cujo resultado vem só da base
# de conhecimento (sem dados pessoais de tools).
INTENTS_CACHEAVEIS = {"institucional"}


def trim_conversation_messages(
    messages: list[AnyMessage],
    max_tokens: int = 4000,
) -> list[AnyMessage]:
    """Poda o histórico de mensagens para respeitar a janela de contexto máxima (RF3-07)."""
    if not messages:
        return []
    try:
        return trim_messages(
            messages,
            max_tokens=max_tokens,
            strategy="last",
            token_counter=len,
            start_on="human",
            end_on=("human", "ai"),
            include_system=True,
        )
    except Exception:
        return messages[-10:]


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
    """Monta o `RunnableConfig` da execução do grafo."""
    return {
        "run_id": run_id,
        "metadata": {
            "message_id": str(run_id),
        },
        "configurable": {
            "thread_id": session_id,
        },
    }


async def sessao_sem_historico(graph: CompiledStateGraph, session_id: str) -> bool:
    """True se a sessão não tem mensagens prévias (T9.2)."""
    try:
        snapshot = await graph.aget_state({"configurable": {"thread_id": session_id}})
        values = getattr(snapshot, "values", None) or {}
        return not values.get("messages")
    except Exception:  # noqa: BLE001
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
