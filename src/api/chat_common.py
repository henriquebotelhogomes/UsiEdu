"""Lógica comum dos endpoints de chat (T7.3).

Centraliza a construção do estado inicial do grafo e do `RunnableConfig`
(com `run_id` adotado pelo LangSmith como id do trace), compartilhados
entre `POST /chat` e `POST /chat/stream`.
"""

from __future__ import annotations

import uuid

from langchain_core.messages import HumanMessage


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
            "message_id": str(run_id),
            "session_id": session_id,
            # Associa a thread ao usuário (T7.4): gravado nos metadados do
            # checkpoint a cada escrita; usado na validação de posse do histórico.
            "user_email": current_user["email"],
        },
        "configurable": {
            "thread_id": session_id,
        },
    }
