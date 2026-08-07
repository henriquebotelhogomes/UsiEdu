"""Configuração de tracing LangSmith.

Conforme RF-30 — toda execução do grafo gera trace no LangSmith
com run name contendo perfil + intenção.
"""

from __future__ import annotations

import os

from langsmith import Client as LangSmithClient

# Configuração do LangSmith via variáveis de ambiente (aceita os dois prefixos)
# LANGSMITH_TRACING=true          (ou LANGCHAIN_TRACING_V2=true)
# LANGSMITH_ENDPOINT=https://api.smith.langchain.com
# LANGSMITH_API_KEY=<key>
# LANGSMITH_PROJECT=usiedu

_client: LangSmithClient | None = None


def _tracing_enabled() -> bool:
    """Verifica se o tracing está habilitado (aceita LANGSMITH_TRACING ou LANGCHAIN_TRACING_V2)."""
    value = os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2", "")
    return value.strip().lower() == "true"


def get_langsmith_client() -> LangSmithClient | None:
    """Retorna o cliente LangSmith se configurado.

    O LangSmith é ativado quando LANGSMITH_TRACING=true (ou o
    equivalente LANGCHAIN_TRACING_V2=true) está definida.
    Caso contrário, retorna None (tracing desligado).
    """
    global _client
    if _client is not None:
        return _client

    if not _tracing_enabled():
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
