"""Servidor MCP para inspeção de SQLite no ecossistema UsiEdu baseado em FastMCP."""

import sqlite3
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

mcp = FastMCP("sqlite-usiedu")

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASES = {
    "checkpoints": BASE_DIR / "usiedu_checkpoints.db",
    "cache": BASE_DIR / "usiedu_cache.db",
    "feedback": BASE_DIR / "usiedu_feedback.db",
}


def _get_connection(db_name: str) -> sqlite3.Connection:
    target = DATABASES.get(db_name.lower())
    if not target:
        # Tenta resolver como caminho relativo ou absoluto
        custom_path = Path(db_name)
        if custom_path.is_file():
            target = custom_path
        elif (BASE_DIR / db_name).is_file():
            target = BASE_DIR / db_name
        else:
            available = list(DATABASES.keys())
            raise ValueError(f"Banco '{db_name}' não encontrado. Opções conhecidas: {available}")

    conn = sqlite3.connect(str(target), timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool()
def list_databases() -> list[str]:
    """Lista os bancos SQLite disponíveis no projeto UsiEdu."""
    return [name for name, path in DATABASES.items() if path.exists()]


@mcp.tool()
def list_tables(db_name: str = "checkpoints") -> list[str]:
    """Lista todas as tabelas em um banco SQLite do UsiEdu ('checkpoints', 'cache', 'feedback')."""
    conn = _get_connection(db_name)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()


@mcp.tool()
def describe_table(table_name: str, db_name: str = "checkpoints") -> list[dict[str, Any]]:
    """Retorna o esquema e as colunas de uma tabela específica."""
    conn = _get_connection(db_name)
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name});")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@mcp.tool()
def read_query(query: str, db_name: str = "checkpoints") -> list[dict[str, Any]]:
    """Executa uma consulta SELECT segura em um dos bancos SQLite do UsiEdu.

    Exemplos:
    - SELECT thread_id, checkpoint_id FROM checkpoints LIMIT 5;
    - SELECT query, similarity_score FROM semantic_cache ORDER BY created_at DESC LIMIT 5;
    """
    clean_query = query.strip()
    if not clean_query.lower().startswith(("select", "pragma", "explain")):
        raise ValueError("Apenas consultas de leitura (SELECT, PRAGMA, EXPLAIN) são permitidas.")

    conn = _get_connection(db_name)
    try:
        cursor = conn.cursor()
        cursor.execute(clean_query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows[:100]]
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run()
