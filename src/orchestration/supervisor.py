"""Nó Supervisor do grafo LangGraph.

Conforme PRD v3 (RF3-01) — classificação de intenção estruturada via Pydantic,
guardrails e roteamento determinístico.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.prompts.supervisor import SUPERVISOR_SYSTEM_PROMPT
from src.orchestration.state import AgentState, SupervisorDecision

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import RunnableConfig


def make_supervisor_node(router_llm: BaseChatModel) -> callable:
    """Factory do nó supervisor com o LLM de roteamento injetado.

    Args:
        router_llm: Modelo LLM usado para classificar intenção.

    Returns:
        Função de nó pronta para o StateGraph.
    """
    if not router_llm:
        msg = "router_llm não pode ser None"
        raise ValueError(msg)

    # Tenta instanciar router estruturado nativo do LangChain
    structured_router = None
    try:
        if hasattr(router_llm, "with_structured_output"):
            structured_router = router_llm.with_structured_output(SupervisorDecision)
    except Exception:
        structured_router = None

    def supervisor_node(state: AgentState, config: RunnableConfig) -> dict:
        """Nó do supervisor: classifica intenção e decide roteamento."""
        messages_text = _format_messages(state["messages"])

        profile = state.get("profile", "student")
        if profile == "staff":
            profile_desc = "staff (funcionário administrativo)"
        else:
            profile_desc = "student (estudante)"

        from src.tools.academico_tools import get_data_atual_formatada

        system_prompt = SUPERVISOR_SYSTEM_PROMPT.format(
            data_atual=get_data_atual_formatada(),
            profile=profile_desc,
            messages=messages_text,
        )

        llm_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["messages"][-1].content if state["messages"] else ""),
        ]

        decision = None

        # 1. Tenta via structured_router (Padrão Enterprise LangChain)
        if structured_router is not None:
            try:
                res = structured_router.invoke(llm_messages)
                if isinstance(res, SupervisorDecision):
                    decision = res
                elif isinstance(res, dict):
                    decision = SupervisorDecision(**res)
            except Exception:
                decision = None

        # 2. Fallback resiliente via parsing JSON
        if decision is None:
            response = router_llm.invoke(llm_messages)
            if hasattr(response, "content"):
                raw = response.content.strip()
            else:
                raw = str(response).strip()

            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                if raw.endswith("```"):
                    raw = raw.rsplit("```", 1)[0]
                raw = raw.strip()

            try:
                data = json.loads(raw)
                decision = SupervisorDecision(**data)
            except Exception:
                decision = SupervisorDecision(
                    intent="academico",
                    plan=None,
                    reasoning=f"Fallback seguro. Raw: {raw[:200]}",
                )

        # Incrementa contador de ciclo
        cycle_count = state.get("cycle_count", 0) + 1

        delegation = {
            "agent": decision.intent,
            "task": decision.reasoning,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return {
            "supervisor_decision": decision,
            "cycle_count": cycle_count,
            "delegations": state.get("delegations", []) + [delegation],
            "agent_results": {},
            "retrieved_sources": [],
        }

    return supervisor_node


def _format_messages(messages: list) -> str:
    """Formata as últimas mensagens para o prompt."""
    text_parts = []
    for msg in messages[-6:]:
        role = "Usuário" if isinstance(msg, HumanMessage) else "Assistente"
        content = msg.content[:500] if isinstance(msg.content, str) else str(msg.content)[:500]
        text_parts.append(f"{role}: {content}")
    return "\n".join(text_parts)


def route_from_supervisor(state: AgentState) -> str | list[str]:
    """Função de roteamento condicional: decide qual(is) agente(s) acionar."""
    decision = state.get("supervisor_decision")
    if not decision:
        return "__end__"

    if hasattr(decision, "intent"):
        intent = decision.intent
    else:
        intent = decision.get("intent", "fora_de_escopo")
    profile = state.get("profile", "student")

    # Guardrail: perfil staff tem acesso a institucional
    if intent == "institucional" and profile != "staff":
        return "__end__"

    if intent == "fora_de_escopo":
        return "fora_de_escopo"

    if intent == "academico":
        return "academico"

    if intent == "financeiro":
        return "financeiro"

    if intent == "institucional":
        return "documental"

    if intent == "composta":
        if profile == "staff":
            return ["academico", "financeiro", "documental"]
        return ["academico", "financeiro"]

    return "__end__"
