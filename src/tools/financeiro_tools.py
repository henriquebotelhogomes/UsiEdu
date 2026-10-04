"""Ferramentas mockadas do Agente Financeiro (RF3-03).

Conforme PRD v3 — funções puras assíncronas e instâncias @tool do LangChain.
"""

from __future__ import annotations

from datetime import date, datetime

from langchain_core.tools import tool

from src.orchestration.context import get_current_datetime_br
from src.tools.mock_data import BOLETOS, POLITICA_RENEGOCIACAO


async def get_boletos(aluno_id: str) -> list[dict]:
    """Consulta boletos emitidos, valores, vencimentos e status financeiro."""
    return list(BOLETOS.get(aluno_id, []))


async def simular_renegociacao(
    aluno_id: str,
    boleto_ids: list[str] | None = None,
    data_referencia: date | None = None,
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

    ref_date = data_referencia or get_current_datetime_br().date()
    desconto_max = POLITICA_RENEGOCIACAO["desconto_maximo_percentual"]
    parcelas_max = POLITICA_RENEGOCIACAO["parcelas_maximas"]
    condicao = POLITICA_RENEGOCIACAO["condicao"]

    boletos_elegiveis: list[tuple[dict, int]] = []
    boletos_inaptos: list[tuple[dict, int]] = []

    for b in boletos_filtrados:
        try:
            venc = datetime.strptime(b["vencimento"], "%Y-%m-%d").date()
            dias_atraso = (ref_date - venc).days
        except Exception:
            dias_atraso = 0

        # Regra de negócio: política válida apenas para boletos com até 30 dias de atraso
        if 0 <= dias_atraso <= 30:
            boletos_elegiveis.append((b, dias_atraso))
        else:
            boletos_inaptos.append((b, dias_atraso))

    if not boletos_elegiveis:
        b_inapto, dias = boletos_inaptos[0]
        return {
            "possivel": False,
            "motivo": (
                f"O boleto {b_inapto['id']} está vencido há {dias} dias. "
                "A política institucional de desconto automático de 10% é válida exclusivamente "
                "para boletos vencidos há menos de 30 dias. Para débitos com mais de 30 dias de "
                "atraso, a negociação deve ser tratada diretamente com a tesouraria/secretaria "
                "financeira, com aplicação dos encargos contratuais cabíveis."
            ),
            "condicao": condicao,
            "dias_atraso": dias,
            "proposta": None,
        }

    valor_total = sum(b["valor"] for b, _ in boletos_elegiveis)
    valor_com_desconto = round(valor_total * (1 - desconto_max / 100), 2)
    valor_parcela = round(valor_com_desconto / parcelas_max, 2)

    return {
        "possivel": True,
        "boletos_abrangidos": [b["id"] for b, _ in boletos_elegiveis],
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
