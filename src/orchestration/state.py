"""Estado do grafo LangGraph (AgentState).

Conforme doc 02 seção 1.2, doc 09 seção 5 e PRD v3.
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


class SupervisorDecision(dict):
    """Decisão estruturada do nó supervisor para classificação e roteamento (RF3-01).

    Compatível com Pydantic, TypedDict e serialização JSON nativa.
    """

    def __init__(
        self,
        intent: Literal[
            "academico", "financeiro", "institucional", "composta", "fora_de_escopo"
        ] = "academico",
        plan: list[str] | None = None,
        reasoning: str = "",
        **kwargs: object,
    ) -> None:
        super().__init__(intent=intent, plan=plan, reasoning=reasoning, **kwargs)

    @property
    def intent(self) -> str:
        return str(self.get("intent", "academico"))

    @property
    def plan(self) -> list[str] | None:
        p = self.get("plan")
        return list(p) if isinstance(p, list) else None

    @property
    def reasoning(self) -> str:
        return str(self.get("reasoning", ""))


class AgentState(TypedDict):
    """Estado completo do grafo de orquestração."""

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
