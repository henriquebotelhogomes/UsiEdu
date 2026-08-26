"""Ferramentas mockadas do Agente Financeiro (RF3-03).

Conforme PRD v3 — funções puras assíncronas e instâncias @tool do LangChain.
"""

from __future__ import annotations

from langchain_core.tools import tool

from src.tools.mock_data import BOLETOS, POLITICA_RENEGOCIACAO


async def get_boletos(aluno_id: str) -> list[dict]:
    """Consulta boletos emitidos, valores, vencimentos e status financeiro."""
    return list(BOLETOS.get(aluno_id, []))


async def simular_renegociacao(
    aluno_id: str,
    boleto_ids: list[str] | None = None,
) -> dict:
    """Simula proposta de renegociação de débitos com base na política vigente."""
    boletos = BOLETOS.get(aluno_id, [])

    if boleto_ids:
        boletos_filtrados = [b for b in boletos if b["id"] in boleto_ids]
    else:
        boletos_filtrados = [b for b in boletos if b.get("status") == "vencido"]

    if not boletos_filtrados:
        return {
            "possivel": False,
            "motivo": "Nenhum boleto vencido encontrado para renegociação.",
            "proposta": None,
        }

    valor_total = sum(b["valor"] for b in boletos_filtrados)
    desconto_max = POLITICA_RENEGOCIACAO["desconto_maximo_percentual"]
    parcelas_max = POLITICA_RENEGOCIACAO["parcelas_maximas"]
    condicao = POLITICA_RENEGOCIACAO["condicao"]

    valor_com_desconto = round(valor_total * (1 - desconto_max / 100), 2)
    valor_parcela = round(valor_com_desconto / parcelas_max, 2)

    return {
        "possivel": True,
        "boletos_abrangidos": [b["id"] for b in boletos_filtrados],
        "valor_original": round(valor_total, 2),
        "desconto_aplicado": f"{desconto_max}%",
        "valor_com_desconto": valor_com_desconto,
        "parcelamento": parcelas_max,
        "valor_parcela": valor_parcela,
        "condicao": condicao,
        "proposta": (
            f"Proposta: {parcelas_max}x de R$ {valor_parcela:.2f} "
            f"(total R$ {valor_com_desconto:.2f}, economia de "
            f"R$ {round(valor_total - valor_com_desconto, 2):.2f})"
        ),
    }


async def get_politica_renegociacao() -> dict:
    """Consulta as regras e percentuais máximos de desconto da política de renegociação vigente."""
    return dict(POLITICA_RENEGOCIACAO)


# Instâncias @tool para binding com LLMs
get_boletos_tool = tool(get_boletos)
simular_renegociacao_tool = tool(simular_renegociacao)
get_politica_renegociacao_tool = tool(get_politica_renegociacao)
FINANCEIRO_TOOLS = [get_boletos_tool, simular_renegociacao_tool, get_politica_renegociacao_tool]
