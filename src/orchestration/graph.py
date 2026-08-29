"""Construtor e compilador do grafo LangGraph de orquestração.

Conforme PRD v3 (RF3-01 a RF3-06) e PRD v4 (RF4-01).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

from src.agents.academico import make_academico_node
from src.agents.documental import make_documental_node
from src.agents.financeiro import make_financeiro_node
from src.orchestration.consolidation import (
    fora_de_escopo_node,
    make_consolidation_node,
    should_continue,
)
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
    synthesis_llm: BaseChatModel | None = None,
    retriever: HybridRetriever | None = None,
    documental_retriever: HybridRetriever | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    interrupt_before: list[str] | None = None,
    interrupt_after: list[str] | None = None,
) -> CompiledStateGraph:
    """Cria e compila o grafo de orquestração do chat (UsiEdu v3 / v4).

    Args:
        router_llm: Modelo LLM para o supervisor (classificação estruturada).
        agent_llm: Modelo LLM para os agentes (execução de tarefas).
        financeiro_llm: Modelo LLM para o agente financeiro (opcional).
        documental_llm: Modelo LLM para o agente documental (opcional).
        synthesis_llm: Modelo LLM para síntese de respostas compostas (opcional).
        retriever: Retriever RAG híbrido da coleção acadêmica.
        documental_retriever: Retriever da coleção institucional.
        checkpointer: Checkpointer LangGraph (MemorySaver por padrão).
        interrupt_before: Lista de nós para pausar antes da execução (Human-in-the-Loop).
        interrupt_after: Lista de nós para pausar após a execução.

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
    builder.add_node(
        "documental", make_documental_node(documental_llm, documental_retriever or retriever)
    )

    # Consolidação com suporte a Síntese Cognitiva (RF3-06)
    builder.add_node("consolidation", make_consolidation_node(synthesis_llm))
    builder.add_node("fora_de_escopo", fora_de_escopo_node)

    # === Arestas ===
    builder.add_edge("__start__", "supervisor")
    builder.add_conditional_edges("supervisor", route_from_supervisor)
    builder.add_edge("academico", "consolidation")
    builder.add_edge("financeiro", "consolidation")
    builder.add_edge("documental", "consolidation")
    builder.add_edge("fora_de_escopo", "__end__")
    builder.add_conditional_edges("consolidation", should_continue)

    # === Checkpointer ===
    if checkpointer is None:
        import os

        db_path = os.getenv("USIEDU_CHECKPOINTER_DB")
        if db_path:
            import aiosqlite
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            conn = aiosqlite.connect(db_path)
            checkpointer = AsyncSqliteSaver(conn)
        else:
            checkpointer = MemorySaver()

    # === Compilação com suporte a Human-in-the-Loop (RF4-01) ===
    graph = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before or [],
        interrupt_after=interrupt_after or [],
    )

    return graph
