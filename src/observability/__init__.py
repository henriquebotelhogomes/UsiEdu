"""Módulo de observabilidade da UsiEdu.

Combina tracing LangSmith e logging JSON estruturado.
"""

from __future__ import annotations

from typing import Any

from src.observability.logging import generate_trace_id, setup_logging


def __getattr__(name: str) -> Any:
    """Adia a dependência opcional do LangSmith para consumidores que precisam dela."""
    if name in {"build_run_name", "get_langsmith_client"}:
        from src.observability import tracing

        return getattr(tracing, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "build_run_name",
    "generate_trace_id",
    "get_langsmith_client",
    "setup_logging",
]
