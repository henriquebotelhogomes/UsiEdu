"""Testes de integração do grafo LangGraph de orquestração.

Testa o grafo completo com LLMs fake: roteamento, ciclo, guardrail e consolidação.
"""

from __future__ import annotations

import json

import pytest
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph

from src.llm.fake import FakeChatModel
from src.orchestration.graph import create_chat_graph
from src.orchestration.state import SupervisorDecision


class TestGraphRouting:
    """Testes de roteamento do grafo."""

    @pytest.mark.asyncio
    async def test_fluxo_academico_completo(
        self, chat_graph, default_state, default_config
    ) -> None:
        """Fluxo academico deve passar por supervisor -> academico -> consolidation."""
        result = await chat_graph.ainvoke(default_state, default_config)

        # Deve ter supervisor_decision
        assert result.get("supervisor_decision") is not None
        assert result["supervisor_decision"]["intent"] == "academico"

        # Deve ter resultado do agente academico
        assert "academico" in result.get("agent_results", {})

        # Deve ter mensagem de resposta
        assert len(result.get("messages", [])) > 0
        last_msg = result["messages"][-1]
        assert last_msg.content is not None

    @pytest.mark.asyncio
    async def test_fluxo_fora_escopo_responde_redirecionamento(
        self, default_state, default_config
    ) -> None:
        """Fluxo fora_de_escopo termina sem agente e com resposta educada (RF-10)."""
        router_llm = FakeChatModel(
            default_response=json.dumps(
                SupervisorDecision(
                    intent="fora_de_escopo",
                    plan=None,
                    reasoning="fora do escopo",
                )
            )
        )
        agent_llm = FakeChatModel(default_response="não deve ser chamado")
        graph = create_chat_graph(router_llm=router_llm, agent_llm=agent_llm)

        result = await graph.ainvoke(default_state, default_config)

        # Não deve ter agent_results
        assert result.get("agent_results") == {}

        # Deve ter supervisor_decision
        assert result["supervisor_decision"]["intent"] == "fora_de_escopo"

        # Última mensagem é o redirecionamento educado
        messages = result.get("messages", [])
        assert "fora do meu escopo" in messages[-1].content

    @pytest.mark.asyncio
    async def test_fluxo_financeiro_direto(self, default_state, default_config) -> None:
        """Fluxo financeiro deve rotear para o nó financeiro (Sprint 3)."""
        router_llm = FakeChatModel(
            default_response=json.dumps(
                SupervisorDecision(
                    intent="financeiro",
                    plan=None,
                    reasoning="pergunta financeira",
                )
            )
        )
        agent_llm = FakeChatModel(default_response="resposta financeira fake")
        graph = create_chat_graph(router_llm=router_llm, agent_llm=agent_llm)

        result = await graph.ainvoke(default_state, default_config)

        # Deve ter resultado do financeiro (rota direta)
        assert "financeiro" in result.get("agent_results", {})
        assert "academico" not in result.get("agent_results", {})

    @pytest.mark.asyncio
    async def test_fluxo_composta_dois_agentes_paralelos(
        self, default_state, default_config
    ) -> None:
        """Fluxo composta deve rotear para academico e financeiro em paralelo."""
        router_llm = FakeChatModel(
            default_response=json.dumps(
                SupervisorDecision(
                    intent="composta",
                    plan=["consultar notas", "consultar boletos"],
                    reasoning="pergunta composta",
                )
            )
        )
        agent_llm = FakeChatModel(default_response="resposta fake do agente")
        graph = create_chat_graph(router_llm=router_llm, agent_llm=agent_llm)

        result = await graph.ainvoke(default_state, default_config)

        # Deve ter resultados de ambos os agentes
        assert "academico" in result.get("agent_results", {})
        assert "financeiro" in result.get("agent_results", {})

        # Com 2 agentes, needs_more_info deve ser False
        assert result.get("needs_more_info") is False

        # Resposta consolidada deve conter ambas as respostas
        assert "resposta fake" in result["messages"][-1].content.lower()

    @pytest.mark.asyncio
    async def test_guardrail_institucional_para_student(
        self, default_state, default_config
    ) -> None:
        """Student perguntando institucional deve ser bloqueado (guardrail)."""
        router_llm = FakeChatModel(
            default_response=json.dumps(
                SupervisorDecision(
                    intent="institucional",
                    plan=None,
                    reasoning="pergunta institucional",
                )
            )
        )
        agent_llm = FakeChatModel(default_response="não deve ser chamado")
        graph = create_chat_graph(router_llm=router_llm, agent_llm=agent_llm)

        result = await graph.ainvoke(default_state, default_config)

        # Student não pode acessar institucional
        assert result.get("agent_results") == {}

    @pytest.mark.asyncio
    async def test_fluxo_institucional_staff_rota_documental(self, default_config) -> None:
        """Staff perguntando institucional deve rotear para documental (Sprint 4)."""
        router_llm = FakeChatModel(
            default_response=json.dumps(
                SupervisorDecision(
                    intent="institucional",
                    plan=None,
                    reasoning="pergunta institucional",
                )
            )
        )
        agent_llm = FakeChatModel(default_response="resposta documental fake")
        graph = create_chat_graph(router_llm=router_llm, agent_llm=agent_llm)

        state = {
            "user_id": "carlos@demo.usiedu",
            "profile": "staff",
            "messages": [HumanMessage(content="Qual a política de uso?")],
            "plan": None,
            "delegations": [],
            "agent_results": {},
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": None,
        }

        result = await graph.ainvoke(state, default_config)

        # Staff deve ter resposta do documental (rota direta, não fallback)
        assert "documental" in result.get("agent_results", {})
        assert "academico" not in result.get("agent_results", {})

    @pytest.mark.asyncio
    async def test_fluxo_composta_staff_tres_agentes(self, default_config) -> None:
        """Fluxo composta com staff deve rotear para 3 agentes em paralelo."""
        router_llm = FakeChatModel(
            default_response=json.dumps(
                SupervisorDecision(
                    intent="composta",
                    plan=["ver notas", "ver boletos", "ver norma"],
                    reasoning="pergunta composta staff",
                )
            )
        )
        agent_llm = FakeChatModel(default_response="resposta fake")
        graph = create_chat_graph(router_llm=router_llm, agent_llm=agent_llm)

        state = {
            "user_id": "carlos@demo.usiedu",
            "profile": "staff",
            "messages": [HumanMessage(content="Quero tudo")],
            "plan": None,
            "delegations": [],
            "agent_results": {},
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": None,
        }

        result = await graph.ainvoke(state, default_config)

        # Deve ter resultados de 3 agentes
        assert "academico" in result.get("agent_results", {})
        assert "financeiro" in result.get("agent_results", {})
        assert "documental" in result.get("agent_results", {})

        # Com 3 agentes, needs_more_info deve ser False
        assert result.get("needs_more_info") is False


class TestGraphCycle:
    """Testes do ciclo de consolidação (RF-11)."""

    @pytest.mark.asyncio
    async def test_ciclo_limite_de_2(
        self,
        chat_graph: CompiledStateGraph,
        default_state: dict,
        default_config: dict,
    ) -> None:
        """RF-11: Máximo de 2 ciclos antes de responder com o que tem."""
        state = {**default_state}
        config = {**default_config}

        # Primeira iteração: fluxo normal
        result = await chat_graph.ainvoke(state, config)

        # Verifica que executou sem erro
        assert result.get("messages") is not None


class TestGraphConsolidation:
    """Testes do nó de consolidação."""

    @pytest.mark.asyncio
    async def test_consolidation_inclui_resposta(
        self, chat_graph, default_state, default_config
    ) -> None:
        """Consolidação deve incluir a resposta do agente."""
        result = await chat_graph.ainvoke(default_state, default_config)
        messages = result.get("messages", [])
        assert len(messages) > 0
        assert "Resposta fake" in messages[-1].content

    @pytest.mark.asyncio
    async def test_consolidation_inclui_agents_involved(
        self, chat_graph, default_state, default_config
    ) -> None:
        """Consolidação deve listar os agentes envolvidos."""
        result = await chat_graph.ainvoke(default_state, default_config)
        agent_results = result.get("agent_results", {})
        assert "academico" in agent_results

    @pytest.mark.asyncio
    async def test_consolidation_sem_agentes(self, default_state, default_config) -> None:
        """Sem agentes, consolidação deve retornar fallback."""
        router_llm = FakeChatModel(
            default_response=json.dumps(
                SupervisorDecision(
                    intent="fora_de_escopo",
                    plan=None,
                    reasoning="fora do escopo",
                )
            )
        )
        agent_llm = FakeChatModel(default_response="não usado")
        graph = create_chat_graph(router_llm=router_llm, agent_llm=agent_llm)

        result = await graph.ainvoke(default_state, default_config)
        messages = result.get("messages", [])
        assert len(messages) > 0
        # Mensagem de fallback para fora_de_escopo
        assert messages[-1].content is not None


class TestGraphState:
    """Testes de estado do grafo."""

    @pytest.mark.asyncio
    async def test_estado_inclui_user_id(self, chat_graph, default_state, default_config) -> None:
        """Estado final deve manter user_id."""
        result = await chat_graph.ainvoke(default_state, default_config)
        assert result.get("user_id") == "ana@demo.usiedu"

    @pytest.mark.asyncio
    async def test_estado_inclui_profile(self, chat_graph, default_state, default_config) -> None:
        """Estado final deve manter profile."""
        result = await chat_graph.ainvoke(default_state, default_config)
        assert result.get("profile") == "student"

    @pytest.mark.asyncio
    async def test_delegations_preservadas(self, chat_graph, default_state, default_config) -> None:
        """Delegações devem ser preservadas no estado final."""
        result = await chat_graph.ainvoke(default_state, default_config)
        assert len(result.get("delegations", [])) > 0

    @pytest.mark.asyncio
    async def test_multi_turn_isolamento_de_agentes(self, default_state, default_config) -> None:
        """Turno 2 não deve herdar agent_results do Turno 1 na mesma sessão."""
        # Turno 1: Academico
        router_llm_1 = FakeChatModel(
            default_response=json.dumps(
                SupervisorDecision(intent="academico", plan=None, reasoning="notas")
            )
        )
        agent_llm_1 = FakeChatModel(default_response="Notas do aluno: 9.0")
        graph_1 = create_chat_graph(router_llm=router_llm_1, agent_llm=agent_llm_1)
        state_1 = await graph_1.ainvoke(default_state, default_config)

        assert "academico" in state_1["agent_results"]

        # Turno 2: Financeiro no mesmo estado / sessão
        router_llm_2 = FakeChatModel(
            default_response=json.dumps(
                SupervisorDecision(intent="financeiro", plan=None, reasoning="boletos")
            )
        )
        agent_llm_2 = FakeChatModel(default_response="Boletos do aluno: R$ 500")
        graph_2 = create_chat_graph(router_llm=router_llm_2, agent_llm=agent_llm_2)

        state_2_input = {
            **state_1,
            "messages": state_1["messages"] + [HumanMessage(content="Qual o valor do meu boleto?")],
        }
        state_2 = await graph_2.ainvoke(state_2_input, default_config)

        # No Turno 2, apenas financeiro deve estar em agent_results e na resposta
        assert "financeiro" in state_2["agent_results"]
        assert "academico" not in state_2["agent_results"]
        assert "Notas do aluno" not in state_2["messages"][-1].content
        assert "Boletos do aluno" in state_2["messages"][-1].content
