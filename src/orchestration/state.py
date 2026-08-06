"""Estado do grafo LangGraph (AgentState).

Conforme doc 02 seção 1.2 e doc 09 seção 5.
"""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

from src.rag.models import Source


def reduce_agent_results(
    current: dict[str, AgentResult] | None,
    update: dict[str, AgentResult] | None,
) -> dict[str, AgentResult]:
    """Reducer para agent_results: merge de dicionários (suporta paralelo)."""
    if current is None:
        current = {}
    if update is None:
        return current
    return {**current, **update}


def reduce_retrieved_sources(
    current: list[Source] | None,
    update: list[Source] | None,
) -> list[Source]:
    """Reducer para retrieved_sources: concatena listas (suporta paralelo)."""
    if current is None:
        current = []
    if update is None:
        return current
    return current + [s for s in update if s not in current]


class Delegation(TypedDict):
    """Registro de delegação de tarefa a um agente."""

    agent: str
    task: str
    timestamp: str


class AgentResult(TypedDict):
    """Resultado parcial produzido por um agente."""

    agent: str
    response: str
    sources: list[Source]
    error: str | None


class SupervisorDecision(TypedDict):
    """Decisão do nó supervisor."""

    intent: Literal["academico", "financeiro", "institucional", "composta", "fora_de_escopo"]
    plan: list[str] | None
    reasoning: str


class AgentState(TypedDict):
    """Estado completo do grafo de orquestração.

    Attributes:
        user_id: Identificador único do usuário.
        profile: Perfil de acesso (student, staff).
        messages: Histórico da conversa (reducer add_messages).
        plan: Sub-tarefas para perguntas compostas.
        delegations: Registro de quem foi acionado e por quê.
        agent_results: Resultados parciais de cada agente.
        retrieved_sources: Fontes RAG usadas (para citação).
        needs_more_info: Se o grafo deve continuar para mais informações.
        cycle_count: Contador de ciclos (limite RF-11: máximo 2).
        supervisor_decision: Última decisão do supervisor.
    """

    user_id: str
    profile: Literal["student", "staff"]
    messages: Annotated[list[AnyMessage], add_messages]
    plan: list[str] | None
    delegations: list[Delegation]
    agent_results: Annotated[dict[str, AgentResult], reduce_agent_results]
    retrieved_sources: Annotated[list[Source], reduce_retrieved_sources]
    needs_more_info: bool
    cycle_count: int
    supervisor_decision: SupervisorDecision | None
