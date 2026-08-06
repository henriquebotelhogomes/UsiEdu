"""Configuração de tracing LangSmith.

Conforme RF-30 — toda execução do grafo gera trace no LangSmith
com run name contendo perfil + intenção.
"""

from __future__ import annotations

import os

from langsmith import Client as LangSmithClient

# Configuração do LangSmith via variáveis de ambiente
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
# LANGCHAIN_API_KEY=<key>
# LANGCHAIN_PROJECT=usiedu

_client: LangSmithClient | None = None


def get_langsmith_client() -> LangSmithClient | None:
    """Retorna o cliente LangSmith se configurado.

    O LangSmith é ativado quando a variável LANGCHAIN_TRACING_V2=true
    está definida. Caso contrário, retorna None (tracing desligado).
    """
    global _client
    if _client is not None:
        return _client

    if os.getenv("LANGCHAIN_TRACING_V2", "").lower() != "true":
        _client = None
        return None

    try:
        _client = LangSmithClient()
        return _client
    except Exception:
        _client = None
        return None


def build_run_name(profile: str, intent: str) -> str:
    """Constrói o nome do run para tracing.

    Formato: "usiedu::{profile}::{intent}"
    Exemplo: "usiedu::student::academico"
    """
    return f"usiedu::{profile}::{intent}"
