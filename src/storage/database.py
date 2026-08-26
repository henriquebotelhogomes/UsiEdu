"""Configuração do banco relacional compartilhado pelo piloto."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator


def database_url() -> str | None:
    """Retorna a URL PostgreSQL configurada, ou ``None`` no modo local SQLite."""
    value = os.getenv("USIEDU_DATABASE_URL", "").strip()
    return value or None


@asynccontextmanager
async def postgres_connection() -> AsyncIterator[object]:
    """Abre uma conexão PostgreSQL somente quando configurada no ambiente."""
    url = database_url()
    if url is None:
        raise RuntimeError("USIEDU_DATABASE_URL não configurada")

    from psycopg import AsyncConnection

    async with await AsyncConnection.connect(url) as connection:
        yield connection


@asynccontextmanager
async def sqlite_connection(path: str) -> AsyncIterator[object]:
    """Abre conexão SQLite com timeout e suporte a Azure Files (CIFS/SMB)."""
    import aiosqlite

    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)

    if path.startswith("/") or path.startswith("file:"):
        conn_path = path if path.startswith("file:") else f"file:{path}?nolock=1"
        uri = True
    else:
        conn_path = path
        uri = False

    async with aiosqlite.connect(conn_path, uri=uri, timeout=30.0) as conn:
        yield conn
