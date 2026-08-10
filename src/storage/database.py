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
