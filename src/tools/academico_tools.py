"""Ferramentas mockadas do Agente Acadêmico.

Conforme doc 09 seção 4 — funções assíncronas puras sobre dados mockados.
"""

from src.tools.mock_data import STUDENTS


async def get_notas(aluno_id: str) -> dict[str, float]:
    """Retorna {disciplina: nota} para um aluno."""
    student = STUDENTS.get(aluno_id)
    if not student:
        return {}
    return dict(student["notas"])


async def get_faltas(aluno_id: str, disciplina: str | None = None) -> int | dict[str, int]:
    """Retorna faltas de um aluno.

    Args:
        aluno_id: ID do aluno.
        disciplina: Nome da disciplina. Se None, retorna todas.

    Returns:
        Total de faltas (int) se disciplina for especificada,
        ou dict[str, int] com todas as disciplinas.
    """
    student = STUDENTS.get(aluno_id)
    if not student:
        return 0 if disciplina else {}

    if disciplina:
        return student["faltas"].get(disciplina, 0)
    return dict(student["faltas"])
