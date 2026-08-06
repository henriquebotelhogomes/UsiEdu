"""Nó Supervisor do grafo LangGraph.

Conforme doc 02 seção 2 — classificação de intenção, guardrails e roteamento.
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

    def supervisor_node(state: AgentState, config: RunnableConfig) -> dict:
        """Nó do supervisor: classifica intenção e decide roteamento.

        Lê a última mensagem do usuário, consulta o LLM de roteamento
        e retorna a decisão estruturada (SupervisorDecision).
        """
        # Extrai histórico recente para o prompt
        messages_text = _format_messages(state["messages"])

        profile = state.get("profile", "student")
        if profile == "staff":
            profile_desc = "staff (funcionário administrativo)"
        else:
            profile_desc = "student (estudante)"

        system_prompt = SUPERVISOR_SYSTEM_PROMPT.format(
            profile=profile_desc,
            messages=messages_text,
        )

        llm_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["messages"][-1].content if state["messages"] else ""),
        ]

        response = router_llm.invoke(llm_messages)
        raw = response.content.strip()

        # Remove delimitadores de código markdown se presentes
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw.rsplit("```", 1)[0]
            raw = raw.strip()

        try:
            decision: SupervisorDecision = json.loads(raw)  # type: ignore[assignment]
        except json.JSONDecodeError:
            # Fallback seguro: academico
            decision = SupervisorDecision(
                intent="academico",
                plan=None,
                reasoning=f"Falha ao parsear resposta do LLM. Raw: {raw[:200]}",
            )

        # Incrementa contador de ciclo
        cycle_count = state.get("cycle_count", 0) + 1

        # Cria delegação
        delegation = {
            "agent": decision.get("intent", "unknown"),
            "task": decision.get("reasoning", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return {
            "supervisor_decision": decision,
            "cycle_count": cycle_count,
            "delegations": state.get("delegations", []) + [delegation],
        }

    return supervisor_node


def _format_messages(messages: list) -> str:
    """Formata as últimas mensagens para o prompt."""
    text_parts = []
    for msg in messages[-6:]:  # últimas 6 mensagens
        role = "Usuário" if isinstance(msg, HumanMessage) else "Assistente"
        content = msg.content[:500] if isinstance(msg.content, str) else str(msg.content)[:500]
        text_parts.append(f"{role}: {content}")
    return "\n".join(text_parts)


def route_from_supervisor(state: AgentState) -> str | list[str]:
    """Função de roteamento condicional: decide qual(is) agente(s) acionar.

    Retorna o nome do(s) próximo(s) nó(s) ou END.
    """
    decision = state.get("supervisor_decision")
    if not decision:
        return "__end__"

    intent = decision.get("intent", "fora_de_escopo")
    profile = state.get("profile", "student")

    # Guardrail: perfil staff tem acesso a institucional
    if intent == "institucional" and profile != "staff":
        return "__end__"

    if intent == "fora_de_escopo":
        return "__end__"

    if intent == "academico":
        return "academico"

    if intent == "financeiro":
        return "financeiro"

    if intent == "institucional":
        return "documental"

    if intent == "composta":
        profile = state.get("profile", "student")
        if profile == "staff":
            return ["academico", "financeiro", "documental"]
        return ["academico", "financeiro"]

    return "__end__"
