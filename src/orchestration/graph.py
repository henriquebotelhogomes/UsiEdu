"""Construtor e compilador do grafo LangGraph de orquestração.

Conforme doc 02 seção 1 e doc 09 seção 5.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

from src.agents.academico import make_academico_node
from src.agents.documental import make_documental_node
from src.agents.financeiro import make_financeiro_node
from src.orchestration.consolidation import consolidation_node, should_continue
from src.orchestration.state import AgentState
from src.orchestration.supervisor import make_supervisor_node, route_from_supervisor

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.state import CompiledStateGraph

    from src.rag.retriever import HybridRetriever


def create_chat_graph(
    router_llm: BaseChatModel,
    agent_llm: BaseChatModel,
    financeiro_llm: BaseChatModel | None = None,
    documental_llm: BaseChatModel | None = None,
    retriever: HybridRetriever | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Cria e compila o grafo de orquestração do chat.

    Args:
        router_llm: Modelo LLM para o supervisor (classificação de intenção).
        agent_llm: Modelo LLM para os agentes (execução de tarefas).
        financeiro_llm: Modelo LLM para o agente financeiro (opcional;
            usa agent_llm se None).
        documental_llm: Modelo LLM para o agente documental (opcional;
            usa agent_llm se None).
        retriever: Retriever RAG híbrido (opcional; sem RAG se None).
        checkpointer: Checkpointer LangGraph (opcional; MemorySaver se None).

    Returns:
        Grafo LangGraph compilado e pronto para invocação.
    """
    builder = StateGraph(AgentState)

    # === Nós (LLMs injetados via factory) ===
    builder.add_node("supervisor", make_supervisor_node(router_llm))
    builder.add_node("academico", make_academico_node(agent_llm, retriever))

    # Se financeiro_llm não for fornecido, usa o mesmo agent_llm
    financeiro_llm = financeiro_llm or agent_llm
    builder.add_node("financeiro", make_financeiro_node(financeiro_llm, retriever))

    # Se documental_llm não for fornecido, usa o mesmo agent_llm
    documental_llm = documental_llm or agent_llm
    builder.add_node("documental", make_documental_node(documental_llm, retriever))

    builder.add_node("consolidation", consolidation_node)

    # === Arestas ===
    builder.add_edge("__start__", "supervisor")
    builder.add_conditional_edges("supervisor", route_from_supervisor)
    builder.add_edge("academico", "consolidation")
    builder.add_edge("financeiro", "consolidation")
    builder.add_edge("documental", "consolidation")
    builder.add_conditional_edges("consolidation", should_continue)

    # === Checkpointer ===
    if checkpointer is None:
        checkpointer = MemorySaver()

    # === Compilação ===
    graph = builder.compile(
        checkpointer=checkpointer,
        interrupt_after=[],
    )

    return graph
