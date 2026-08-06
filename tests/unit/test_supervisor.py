"""Testes do nó Supervisor e roteamento condicional."""

from __future__ import annotations

import pytest

from src.orchestration.state import SupervisorDecision
from src.orchestration.supervisor import make_supervisor_node, route_from_supervisor


class TestSupervisorNode:
    """Testes do nó supervisor."""

    def test_supervisor_retorna_decision_com_intent(self, fake_router_llm, default_state) -> None:
        """Supervisor deve retornar SupervisorDecision com intent."""
        node = make_supervisor_node(fake_router_llm)
        result = node(default_state, {})
        decision = result.get("supervisor_decision")
        assert decision is not None
        assert decision.get("intent") in (
            "academico",
            "financeiro",
            "institucional",
            "composta",
            "fora_de_escopo",
        )

    def test_supervisor_incrementa_cycle_count(self, fake_router_llm, default_state) -> None:
        """cycle_count deve ser incrementado em 1."""
        node = make_supervisor_node(fake_router_llm)
        result = node(default_state, {})
        assert result.get("cycle_count") == 1

    def test_supervisor_cria_delegacao(self, fake_router_llm, default_state) -> None:
        """Deve criar uma delegação com timestamp."""
        node = make_supervisor_node(fake_router_llm)
        result = node(default_state, {})
        delegations = result.get("delegations", [])
        assert len(delegations) == 1
        assert delegations[0]["agent"] == "academico"
        assert "timestamp" in delegations[0]

    def test_supervisor_sem_router_llm_leva_erro(self, default_state) -> None:
        """Sem router_llm na factory, deve levantar ValueError."""
        with pytest.raises(ValueError, match="router_llm não pode ser None"):
            make_supervisor_node(None)  # type: ignore[arg-type]

    def test_supervisor_com_mensagens_vazias(self, fake_router_llm) -> None:
        """Com mensagens vazias, deve funcionar sem erro."""
        state = {
            "user_id": "test",
            "profile": "student",
            "messages": [],
            "plan": None,
            "delegations": [],
            "agent_results": {},
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": None,
        }
        node = make_supervisor_node(fake_router_llm)
        result = node(state, {})
        assert result.get("supervisor_decision") is not None

    def test_supervisor_com_json_invalido_fallback_academico(
        self, fake_router_llm, default_state
    ) -> None:
        """Resposta inválida do LLM deve fallback para intent academico."""
        llm = fake_router_llm
        llm.default_response = "resposta não json"
        node = make_supervisor_node(llm)
        result = node(default_state, {})
        decision = result.get("supervisor_decision")
        assert decision.get("intent") == "academico"


class TestRouteFromSupervisor:
    """Testes da função de roteamento condicional."""

    def test_intent_academico_rota_para_academico(self) -> None:
        """Intent academico deve rotear para nó academico."""
        state = {
            "supervisor_decision": SupervisorDecision(
                intent="academico", plan=None, reasoning="teste"
            ),
            "profile": "student",
        }
        assert route_from_supervisor(state) == "academico"  # type: ignore[arg-type]

    def test_intent_fora_escopo_rota_para_no_de_redirecionamento(self) -> None:
        """Intent fora_de_escopo deve rotear para o nó fora_de_escopo (RF-10)."""
        state = {
            "supervisor_decision": SupervisorDecision(
                intent="fora_de_escopo", plan=None, reasoning="teste"
            ),
            "profile": "student",
        }
        assert route_from_supervisor(state) == "fora_de_escopo"  # type: ignore[arg-type]

    def test_intent_financeiro_rota_direta(self) -> None:
        """Intent financeiro deve rotear para o nó financeiro (Sprint 3)."""
        state = {
            "supervisor_decision": SupervisorDecision(
                intent="financeiro", plan=None, reasoning="teste"
            ),
            "profile": "student",
        }
        assert route_from_supervisor(state) == "financeiro"  # type: ignore[arg-type]

    def test_intent_composta_rota_lista_dois_agentes(self) -> None:
        """Intent composta deve rotear para lista com academico e financeiro."""
        state = {
            "supervisor_decision": SupervisorDecision(
                intent="composta",
                plan=["consultar notas", "consultar boletos"],
                reasoning="teste",
            ),
            "profile": "student",
        }
        result = route_from_supervisor(state)  # type: ignore[arg-type]
        assert isinstance(result, list)
        assert "academico" in result
        assert "financeiro" in result

    def test_institucional_student_vai_para_end(self) -> None:
        """Intent institucional com perfil student deve ir para END (guardrail)."""
        state = {
            "supervisor_decision": SupervisorDecision(
                intent="institucional", plan=None, reasoning="teste"
            ),
            "profile": "student",
        }
        assert route_from_supervisor(state) == "__end__"  # type: ignore[arg-type]

    def test_institucional_staff_rota_documental(self) -> None:
        """Intent institucional com perfil staff deve rotear para documental."""
        state = {
            "supervisor_decision": SupervisorDecision(
                intent="institucional", plan=None, reasoning="teste"
            ),
            "profile": "staff",
        }
        assert route_from_supervisor(state) == "documental"  # type: ignore[arg-type]

    def test_composta_staff_rota_tres_agentes(self) -> None:
        """Intent composta com perfil staff deve incluir documental."""
        state = {
            "supervisor_decision": SupervisorDecision(
                intent="composta",
                plan=["consultar notas", "consultar boletos", "ver norma"],
                reasoning="teste",
            ),
            "profile": "staff",
        }
        result = route_from_supervisor(state)  # type: ignore[arg-type]
        assert isinstance(result, list)
        assert "academico" in result
        assert "financeiro" in result
        assert "documental" in result
        assert len(result) == 3

    def test_composta_student_rota_dois_agentes(self) -> None:
        """Intent composta com perfil student não deve incluir documental."""
        state = {
            "supervisor_decision": SupervisorDecision(
                intent="composta",
                plan=["consultar notas", "consultar boletos"],
                reasoning="teste",
            ),
            "profile": "student",
        }
        result = route_from_supervisor(state)  # type: ignore[arg-type]
        assert isinstance(result, list)
        assert "academico" in result
        assert "financeiro" in result
        assert "documental" not in result
        assert len(result) == 2

    def test_sem_decision_vai_para_end(self) -> None:
        """Sem supervisor_decision deve ir para END."""
        state = {"supervisor_decision": None, "profile": "student"}
        assert route_from_supervisor(state) == "__end__"  # type: ignore[arg-type]
