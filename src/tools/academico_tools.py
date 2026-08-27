"""Ferramentas mockadas e utilitários de calendário do Agente Acadêmico (RF3-03).

Conforme PRD v3 — funções puras assíncronas e instâncias @tool do LangChain.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from langchain_core.tools import tool

from src.tools.mock_data import STUDENTS

# Feriados e recessos oficiais previstos no 2º semestre de 2026
FERIADOS_2026_2 = {
    date(2026, 9, 7): "Independência do Brasil",
    date(2026, 10, 12): "Nossa Senhora Aparecida",
    date(2026, 10, 28): "Dia do Servidor Público",
    date(2026, 11, 2): "Finados",
    date(2026, 11, 15): "Proclamação da República",
    date(2026, 11, 20): "Dia Nacional de Zumbi e da Consciência Negra",
    date(2026, 11, 30): "Dia do Evangélico (DF)",
}

DATA_FIM_AULAS_2026_2 = date(2026, 12, 14)
DATA_FIM_PERIODO_2026_2 = date(2026, 12, 19)


def get_data_atual_referencia() -> date:
    """Retorna a data atual no fuso horário do Brasil (UTC-3)."""
    br_tz = timezone(timedelta(hours=-3))
    return datetime.now(br_tz).date()


def get_data_atual_formatada() -> str:
    """Retorna a data atual por extenso e em formato padrão."""
    hoje = get_data_atual_referencia()
    dias_semana = [
        "segunda-feira",
        "terça-feira",
        "quarta-feira",
        "quinta-feira",
        "sexta-feira",
        "sábado",
        "domingo",
    ]
    meses = [
        "janeiro",
        "fevereiro",
        "março",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro",
    ]
    dia_semana = dias_semana[hoje.weekday()]
    mes = meses[hoje.month - 1]
    return f"{hoje.strftime('%d/%m/%Y')} ({dia_semana}, {hoje.day} de {mes} de {hoje.year})"


async def get_data_atual() -> dict[str, Any]:
    """Retorna a data atual do sistema com dia da semana e ano."""
    hoje = get_data_atual_referencia()
    return {
        "data": hoje.isoformat(),
        "formatada": get_data_atual_formatada(),
        "ano": hoje.year,
        "mes": hoje.month,
        "dia": hoje.day,
    }


async def calcular_dias_letivos_restantes(
    data_inicio: str | None = None,
) -> dict[str, Any]:
    """Calcula os dias letivos e dias de aula restantes no semestre/ano letivo de 2026.2.

    Args:
        data_inicio: Data de referência no formato YYYY-MM-DD (padrão: hoje).
    """
    if data_inicio:
        try:
            hoje = date.fromisoformat(data_inicio)
        except ValueError:
            hoje = get_data_atual_referencia()
    else:
        hoje = get_data_atual_referencia()

    # Conta dias de aula (segunda a sexta, exceto feriados) até o último dia de aulas
    dias_aulas_restantes = 0
    curr = hoje + timedelta(days=1) if hoje < DATA_FIM_AULAS_2026_2 else hoje
    feriados_no_periodo = []

    while curr <= DATA_FIM_AULAS_2026_2:
        if curr.weekday() < 5:  # Segunda a Sexta
            if curr in FERIADOS_2026_2:
                feriados_no_periodo.append(f"{curr.strftime('%d/%m/%Y')} ({FERIADOS_2026_2[curr]})")
            else:
                dias_aulas_restantes += 1
        curr += timedelta(days=1)

    # Conta dias letivos totais (segunda a sábado, exceto feriados) até o fim do período letivo
    dias_letivos_restantes = 0
    curr = hoje + timedelta(days=1) if hoje < DATA_FIM_PERIODO_2026_2 else hoje

    while curr <= DATA_FIM_PERIODO_2026_2:
        if curr.weekday() < 6:  # Segunda a Sábado
            if curr not in FERIADOS_2026_2:
                dias_letivos_restantes += 1
        curr += timedelta(days=1)

    return {
        "data_referencia": hoje.strftime("%d/%m/%Y"),
        "ultimo_dia_aulas": DATA_FIM_AULAS_2026_2.strftime("%d/%m/%Y"),
        "ultimo_dia_periodo_letivo": DATA_FIM_PERIODO_2026_2.strftime("%d/%m/%Y"),
        "dias_de_aulas_restantes": dias_aulas_restantes,
        "dias_letivos_totais_restantes": dias_letivos_restantes,
        "feriados_restantes": feriados_no_periodo,
    }


async def get_notas(aluno_id: str) -> dict[str, float]:
    """Consulta o histórico escolar e retorna as notas do estudante por disciplina."""
    student = STUDENTS.get(aluno_id)
    if not student:
        return {}
    return dict(student["notas"])


async def get_faltas(aluno_id: str, disciplina: str | None = None) -> int | dict[str, int]:
    """Consulta a frequência e total de faltas do estudante em uma ou todas as disciplinas."""
    student = STUDENTS.get(aluno_id)
    if not student:
        return 0 if disciplina else {}

    if disciplina:
        return student["faltas"].get(disciplina, 0)
    return dict(student["faltas"])


# Instâncias @tool para binding com LLMs
get_notas_tool = tool(get_notas)
get_faltas_tool = tool(get_faltas)
get_data_atual_tool = tool(get_data_atual)
calcular_dias_letivos_tool = tool(calcular_dias_letivos_restantes)

ACADEMICO_TOOLS = [
    get_notas_tool,
    get_faltas_tool,
    get_data_atual_tool,
    calcular_dias_letivos_tool,
]
