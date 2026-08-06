"""Ferramentas mockadas do Agente Financeiro.

Conforme doc 09 seção 4 — funções assíncronas puras sobre dados mockados.
"""

from src.tools.mock_data import BOLETOS, POLITICA_RENEGOCIACAO


async def get_boletos(aluno_id: str) -> list[dict]:
    """Retorna lista de boletos de um aluno.

    Args:
        aluno_id: ID do aluno.

    Returns:
        Lista de dicionários com id, valor, vencimento, status.
    """
    return list(BOLETOS.get(aluno_id, []))


async def simular_renegociacao(
    aluno_id: str,
    boleto_ids: list[str] | None = None,
) -> dict:
    """Simula uma proposta de renegociação com base na política vigente.

    Aplica a política de renegociação (desconto máximo, parcelas máximas)
    aos boletos vencidos do aluno.

    Args:
        aluno_id: ID do aluno.
        boleto_ids: Lista de IDs de boletos para renegociar.
            Se None, considera todos os boletos vencidos.

    Returns:
        Dicionário com proposta de renegociação.
    """
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
    """Retorna a política de renegociação vigente."""
    return dict(POLITICA_RENEGOCIACAO)
