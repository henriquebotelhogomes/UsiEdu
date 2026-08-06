"""Testes do Agente Documental."""

from __future__ import annotations

import pytest


class TestDocumentalNode:
    """Testes do nó Agente Documental."""

    @pytest.mark.asyncio
    async def test_documental_node_com_llm_fake(self, fake_agent_llm) -> None:
        """Nó documental com LLM fake deve processar e retornar resultado."""
        from src.agents.documental import make_documental_node

        node = make_documental_node(fake_agent_llm)
        state = {
            "user_id": "carlos@demo.usiedu",
            "profile": "staff",
            "messages": [],
            "plan": None,
            "delegations": [],
            "agent_results": {},
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": None,
        }
        result = await node(state, {})

        assert "documental" in result.get("agent_results", {})
        doc_result = result["agent_results"]["documental"]
        assert doc_result["agent"] == "documental"
        assert doc_result["response"] is not None
        assert doc_result["error"] is None

    @pytest.mark.asyncio
    async def test_documental_node_sem_llm_leva_erro(self) -> None:
        """Sem agent_llm na factory, deve levantar ValueError."""
        from src.agents.documental import make_documental_node

        with pytest.raises(ValueError, match="agent_llm não pode ser None"):
            make_documental_node(None)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_documental_node_com_mensagens_vazias(self, fake_agent_llm) -> None:
        """Com mensagens vazias, deve funcionar sem erro."""
        from src.agents.documental import make_documental_node

        state = {
            "user_id": "carlos@demo.usiedu",
            "profile": "staff",
            "messages": [],
            "plan": None,
            "delegations": [],
            "agent_results": {},
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": None,
        }
        node = make_documental_node(fake_agent_llm)
        result = await node(state, {})
        assert "documental" in result.get("agent_results", {})
