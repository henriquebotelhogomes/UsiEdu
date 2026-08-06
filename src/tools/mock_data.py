"""Dados mockados para ferramentas dos agentes.

Conforme doc 09 seção 4 — dados de demonstração, nunca I/O real.
"""

STUDENTS: dict[str, dict] = {
    "ana-123": {
        "nome": "Ana Souza",
        "curso": "ADS",
        "periodo": 1,
        "notas": {"calculo-1": 5.8, "programacao-1": 9.1},
        "faltas": {"calculo-1": 6, "programacao-1": 0},
    },
}

BOLETOS: dict[str, list[dict]] = {
    "ana-123": [
        {
            "id": "bol-001",
            "valor": 890.00,
            "vencimento": "2026-07-10",
            "status": "vencido",
        },
    ],
}

POLITICA_RENEGOCIACAO: dict = {
    "desconto_maximo_percentual": 10,
    "parcelas_maximas": 6,
    "condicao": "apenas boletos vencidos há menos de 30 dias",
}

USUARIOS_DEMO: dict[str, dict] = {
    "ana@demo.usiedu": {
        "password": "estudante123",
        "profile": "student",
        "display_name": "Ana Souza",
        "aluno_id": "ana-123",
    },
    "carlos@demo.usiedu": {
        "password": "staff123",
        "profile": "staff",
        "display_name": "Carlos Oliveira",
        "aluno_id": None,
    },
}
