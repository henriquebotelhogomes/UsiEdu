"""Configuração do banco relacional compartilhado pelo piloto."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator


def database_url() -> str | None:
    """Retorna a URL PostgreSQL configurada, ou ``None`` no modo local SQLite."""
    value = os.getenv("USIEDU_DATABASE_URL", "").strip()
    return value or None


def postgres_connect_timeout_seconds() -> float:
    """Retorna timeout de conexão PostgreSQL, sem retry para evitar duplicação."""
    try:
        timeout = float(os.getenv("USIEDU_POSTGRES_CONNECT_TIMEOUT_SECONDS", "10"))
    except ValueError:
        return 10.0
    return timeout if timeout > 0 else 10.0


@asynccontextmanager
async def postgres_connection() -> AsyncIterator[object]:
    """Abre uma conexão PostgreSQL somente quando configurada no ambiente."""
    url = database_url()
    if url is None:
        raise RuntimeError("USIEDU_DATABASE_URL não configurada")

    from psycopg import AsyncConnection

    async with await AsyncConnection.connect(
        url, connect_timeout=postgres_connect_timeout_seconds()
    ) as connection:
        yield connection
