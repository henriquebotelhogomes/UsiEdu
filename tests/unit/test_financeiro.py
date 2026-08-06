"""Testes do Agente Financeiro e ferramentas financeiras."""

from __future__ import annotations

import pytest

from src.tools.financeiro_tools import get_boletos, get_politica_renegociacao, simular_renegociacao


class TestFinanceiroTools:
    """Testes das ferramentas do agente financeiro."""

    @pytest.mark.asyncio
    async def test_get_boletos_aluno_existente(self) -> None:
        """Aluno existente deve ter boletos."""
        boletos = await get_boletos("ana-123")
        assert len(boletos) > 0
        assert boletos[0]["id"] == "bol-001"
        assert boletos[0]["valor"] == 890.00
        assert boletos[0]["status"] == "vencido"

    @pytest.mark.asyncio
    async def test_get_boletos_aluno_inexistente(self) -> None:
        """Aluno inexistente deve retornar lista vazia."""
        boletos = await get_boletos("inexistente")
        assert boletos == []

    @pytest.mark.asyncio
    async def test_simular_renegociacao_com_boletos_vencidos(self) -> None:
        """Renegociação com boletos vencidos deve retornar proposta."""
        resultado = await simular_renegociacao("ana-123")
        assert resultado["possivel"] is True
        assert resultado["boletos_abrangidos"] == ["bol-001"]
        assert resultado["valor_original"] == 890.00
        assert resultado["desconto_aplicado"] == "10%"
        assert resultado["parcelamento"] == 6
        assert "Proposta:" in resultado["proposta"]

    @pytest.mark.asyncio
    async def test_simular_renegociacao_sem_boletos_vencidos(self) -> None:
        """Sem boletos vencidos deve retornar impossível."""
        resultado = await simular_renegociacao("aluno-sem-boletos")
        assert resultado["possivel"] is False
        assert "Nenhum boleto vencido" in resultado["motivo"]

    @pytest.mark.asyncio
    async def test_simular_renegociacao_com_boleto_ids_especificos(self) -> None:
        """Renegociação com IDs específicos deve filtrar corretamente."""
        resultado = await simular_renegociacao("ana-123", boleto_ids=["bol-001"])
        assert resultado["possivel"] is True
        assert resultado["boletos_abrangidos"] == ["bol-001"]

    @pytest.mark.asyncio
    async def test_get_politica_renegociacao(self) -> None:
        """Política de renegociação deve conter as chaves esperadas."""
        politica = await get_politica_renegociacao()
        assert "desconto_maximo_percentual" in politica
        assert "parcelas_maximas" in politica
        assert "condicao" in politica
        assert politica["desconto_maximo_percentual"] == 10
        assert politica["parcelas_maximas"] == 6


class TestFinanceiroNode:
    """Testes do nó Agente Financeiro."""

    @pytest.mark.asyncio
    async def test_financeiro_node_com_llm_fake(self, fake_agent_llm, default_state) -> None:
        """Nó financeiro com LLM fake deve processar e retornar resultado."""
        from src.agents.financeiro import make_financeiro_node

        node = make_financeiro_node(fake_agent_llm)
        result = await node(default_state, {})

        assert "financeiro" in result.get("agent_results", {})
        financeiro_result = result["agent_results"]["financeiro"]
        assert financeiro_result["agent"] == "financeiro"
        assert financeiro_result["response"] is not None
        assert financeiro_result["error"] is None

    @pytest.mark.asyncio
    async def test_financeiro_node_sem_llm_leva_erro(self) -> None:
        """Sem agent_llm na factory, deve levantar ValueError."""
        from src.agents.financeiro import make_financeiro_node

        with pytest.raises(ValueError, match="agent_llm não pode ser None"):
            make_financeiro_node(None)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_financeiro_node_com_mensagens_vazias(self, fake_agent_llm) -> None:
        """Com mensagens vazias, deve funcionar sem erro."""
        from src.agents.financeiro import make_financeiro_node

        state = {
            "user_id": "ana@demo.usiedu",
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
        node = make_financeiro_node(fake_agent_llm)
        result = await node(state, {})
        assert "financeiro" in result.get("agent_results", {})
