"""Ferramentas do Agente Acadêmico (RF3-03, RF3-04).

Conforme PRD v3 — funções assíncronas transacionais e instâncias @tool do LangChain
para consulta a dados acadêmicos privados de estudantes.
"""

from __future__ import annotations

from langchain_core.tools import tool

from src.tools.mock_data import STUDENTS


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


# Instâncias @tool para binding nativo com LLMs
get_notas_tool = tool(get_notas)
get_faltas_tool = tool(get_faltas)

ACADEMICO_TOOLS = [
    get_notas_tool,
    get_faltas_tool,
]
