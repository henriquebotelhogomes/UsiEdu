"""Testes do nó de Consolidação."""

from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from src.orchestration.consolidation import (
    consolidation_node,
    should_continue,
)
from src.orchestration.state import AgentResult, SupervisorDecision


class TestConsolidationNode:
    """Testes do nó de consolidação."""

    @pytest.mark.asyncio
    async def test_consolidation_com_resultado_agente(self) -> None:
        """Com resultado de agente, deve retornar resposta consolidada."""
        state = {
            "user_id": "test",
            "profile": "student",
            "messages": [HumanMessage(content="teste")],
            "plan": None,
            "delegations": [],
            "agent_results": {
                "academico": AgentResult(
                    agent="academico",
                    response="Resposta do agente acadêmico",
                    sources=[],
                    error=None,
                ),
            },
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": None,
        }
        result = await consolidation_node(state)
        messages = result.get("messages", [])
        assert len(messages) > 0
        assert "Resposta do agente" in messages[-1].content

    @pytest.mark.asyncio
    async def test_consolidation_sem_agentes_retorna_fallback(self) -> None:
        """Sem agent_results, deve retornar mensagem de fallback."""
        state = {
            "user_id": "test",
            "profile": "student",
            "messages": [HumanMessage(content="teste")],
            "plan": None,
            "delegations": [],
            "agent_results": {},
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": None,
        }
        result = await consolidation_node(state)
        messages = result.get("messages", [])
        assert len(messages) > 0
        assert "reformular" in messages[-1].content.lower()

    @pytest.mark.asyncio
    async def test_consolidation_com_erro_no_agente(self) -> None:
        """Agente com erro deve ter mensagem de erro na resposta."""
        state = {
            "user_id": "test",
            "profile": "student",
            "messages": [HumanMessage(content="teste")],
            "plan": None,
            "delegations": [],
            "agent_results": {
                "academico": AgentResult(
                    agent="academico",
                    response="",
                    sources=[],
                    error="Erro de conexão",
                ),
            },
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": None,
        }
        result = await consolidation_node(state)
        messages = result.get("messages", [])
        assert "Erro de conexão" in messages[-1].content

    @pytest.mark.asyncio
    async def test_consolidation_pergunta_composta_incompleta(self) -> None:
        """Pergunta composta com apenas 1 agente deve ter needs_more_info=True."""
        state = {
            "user_id": "test",
            "profile": "student",
            "messages": [HumanMessage(content="teste")],
            "plan": ["sub1", "sub2"],
            "delegations": [],
            "agent_results": {
                "academico": AgentResult(
                    agent="academico",
                    response="Resposta parcial",
                    sources=[],
                    error=None,
                ),
            },
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": SupervisorDecision(
                intent="composta", plan=["sub1", "sub2"], reasoning="teste"
            ),
        }
        result = await consolidation_node(state)
        assert result.get("needs_more_info") is True

    @pytest.mark.asyncio
    async def test_consolidation_pergunta_composta_completa(self) -> None:
        """Pergunta composta com 2 agentes deve ter needs_more_info=False."""
        state = {
            "user_id": "test",
            "profile": "student",
            "messages": [HumanMessage(content="teste")],
            "plan": ["consultar notas", "consultar boletos"],
            "delegations": [],
            "agent_results": {
                "academico": AgentResult(
                    agent="academico",
                    response="Resposta acadêmica",
                    sources=[],
                    error=None,
                ),
                "financeiro": AgentResult(
                    agent="financeiro",
                    response="Resposta financeira",
                    sources=[],
                    error=None,
                ),
            },
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": SupervisorDecision(
                intent="composta", plan=["consultar notas", "consultar boletos"], reasoning="teste"
            ),
        }
        result = await consolidation_node(state)
        assert result.get("needs_more_info") is False
        # Deve conter respostas de ambos os agentes
        assert "Resposta acadêmica" in result["messages"][-1].content
        assert "Resposta financeira" in result["messages"][-1].content

    @pytest.mark.asyncio
    async def test_consolidation_nao_contradicao(self) -> None:
        """Consolidação com 2 agentes não deve produzir contradição."""
        state = {
            "user_id": "test",
            "profile": "student",
            "messages": [HumanMessage(content="teste")],
            "plan": None,
            "delegations": [],
            "agent_results": {
                "academico": AgentResult(
                    agent="academico",
                    response="Sua nota em Cálculo 1 é 5.8.",
                    sources=[],
                    error=None,
                ),
                "financeiro": AgentResult(
                    agent="financeiro",
                    response="Seu boleto de R$ 890,00 está vencido.",
                    sources=[],
                    error=None,
                ),
            },
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": None,
        }
        result = await consolidation_node(state)
        content = result["messages"][-1].content

        # Ambas as respostas devem estar presentes
        assert "Cálculo 1" in content
        assert "R$ 890,00" in content

    @pytest.mark.asyncio
    async def test_consolidation_sem_pergunta_composta(self) -> None:
        """Pergunta simples não deve ter needs_more_info."""
        state = {
            "user_id": "test",
            "profile": "student",
            "messages": [HumanMessage(content="teste")],
            "plan": None,
            "delegations": [],
            "agent_results": {
                "academico": AgentResult(
                    agent="academico",
                    response="Resposta completa",
                    sources=[],
                    error=None,
                ),
            },
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": None,
        }
        result = await consolidation_node(state)
        assert result.get("needs_more_info") is False


class TestShouldContinue:
    """Testes da função de roteamento pós-consolidação."""

    def test_needs_more_info_e_ciclo_abaixo_limite_retorna_supervisor(self) -> None:
        """Com needs_more_info e cycle_count < 2, deve retornar 'supervisor'."""
        state = {"needs_more_info": True, "cycle_count": 1}
        assert should_continue(state) == "supervisor"  # type: ignore[arg-type]

    def test_sem_needs_more_info_retorna_end(self) -> None:
        """Sem needs_more_info, deve retornar END."""
        state = {"needs_more_info": False, "cycle_count": 0}
        assert should_continue(state) == "__end__"  # type: ignore[arg-type]

    def test_ciclo_excede_limite_retorna_end(self) -> None:
        """Com cycle_count >= 2, deve retornar END mesmo com needs_more_info."""
        state = {"needs_more_info": True, "cycle_count": 2}
        assert should_continue(state) == "__end__"  # type: ignore[arg-type]

    def test_ciclo_no_limite_retorna_supervisor(self) -> None:
        """Com cycle_count < 2 e needs_more_info, deve retornar supervisor."""
        state = {"needs_more_info": True, "cycle_count": 1}
        assert should_continue(state) == "supervisor"  # type: ignore[arg-type]
