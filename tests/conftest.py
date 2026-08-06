"""Fixtures compartilhadas para a suíte de testes da UsiEdu."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from langchain_core.messages import HumanMessage

from src.llm.fake import FakeChatModel
from src.orchestration.graph import create_chat_graph
from src.orchestration.state import SupervisorDecision

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph


@pytest.fixture
def fake_router_llm() -> FakeChatModel:
    """LLM fake com respostas padrão para o supervisor."""
    return FakeChatModel(
        default_response=json.dumps(
            SupervisorDecision(
                intent="academico",
                plan=None,
                reasoning="teste fake",
            )
        )
    )


@pytest.fixture
def fake_agent_llm() -> FakeChatModel:
    """LLM fake para o agente acadêmico."""
    return FakeChatModel(default_response="Resposta fake do agente acadêmico para teste.")


@pytest.fixture
def fake_router_fora_escopo() -> FakeChatModel:
    """LLM fake que retorna 'fora_de_escopo'."""
    return FakeChatModel(
        default_response=json.dumps(
            SupervisorDecision(
                intent="fora_de_escopo",
                plan=None,
                reasoning="mensagem fora do escopo institucional",
            )
        )
    )


@pytest.fixture
def fake_router_composta() -> FakeChatModel:
    """LLM fake que retorna 'composta'."""
    return FakeChatModel(
        default_response=json.dumps(
            SupervisorDecision(
                intent="composta",
                plan=["consultar notas", "consultar boletos"],
                reasoning="pergunta envolve múltiplas categorias",
            )
        )
    )


@pytest.fixture
def fake_router_financeiro() -> FakeChatModel:
    """LLM fake que retorna 'financeiro'."""
    return FakeChatModel(
        default_response=json.dumps(
            SupervisorDecision(
                intent="financeiro",
                plan=None,
                reasoning="pergunta sobre financeiro",
            )
        )
    )


@pytest.fixture
def fake_router_institucional() -> FakeChatModel:
    """LLM fake que retorna 'institucional'."""
    return FakeChatModel(
        default_response=json.dumps(
            SupervisorDecision(
                intent="institucional",
                plan=None,
                reasoning="pergunta sobre documentos institucionais",
            )
        )
    )


@pytest.fixture
def chat_graph(
    fake_router_llm: FakeChatModel,
    fake_agent_llm: FakeChatModel,
) -> CompiledStateGraph:
    """Grafo LangGraph compilado com LLMs fake."""
    graph = create_chat_graph(
        router_llm=fake_router_llm,
        agent_llm=fake_agent_llm,
        retriever=None,
    )
    return graph


@pytest.fixture
def chat_graph_sem_retriever(
    fake_router_llm: FakeChatModel,
    fake_agent_llm: FakeChatModel,
) -> CompiledStateGraph:
    """Grafo sem retriever (caso RAG não configurado)."""
    return create_chat_graph(
        router_llm=fake_router_llm,
        agent_llm=fake_agent_llm,
        retriever=None,
    )


@pytest.fixture
def default_state() -> dict:
    """Estado inicial padrão para testes."""
    return {
        "user_id": "ana@demo.usiedu",
        "profile": "student",
        "messages": [HumanMessage(content="Quero ver minhas notas")],
        "plan": None,
        "delegations": [],
        "agent_results": {},
        "retrieved_sources": [],
        "needs_more_info": False,
        "cycle_count": 0,
        "supervisor_decision": None,
    }


@pytest.fixture
def default_config() -> dict:
    """Configuração padrão (thread_id mockado)."""
    return {
        "configurable": {
            "thread_id": "test-session-001",
        }
    }
