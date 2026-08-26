"""Medições sanitizadas de duração e falhas dos componentes locais."""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Protocol


class MeasurementLogger(Protocol):
    """Interface mínima do logger usada para medir componentes."""

    def info(self, message: str, *, extra: dict[str, object]) -> None: ...

    def warning(self, message: str, *, extra: dict[str, object]) -> None: ...


@contextmanager
def component_measurement(
    *,
    logger: MeasurementLogger,
    component: str,
    operation: str,
    item_count: int,
    backend: str,
) -> Generator[None, None, None]:
    """Registra resultado agregado sem serializar entrada, saída ou exceção."""
    started = time.perf_counter()
    try:
        yield
    except Exception:
        logger.warning(
            "Component measurement failed",
            extra={
                "component": component,
                "operation": operation,
                "outcome": "error",
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "item_count": item_count,
                "backend": backend,
            },
        )
        raise
    else:
        logger.info(
            "Component measurement completed",
            extra={
                "component": component,
                "operation": operation,
                "outcome": "success",
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "item_count": item_count,
                "backend": backend,
            },
        )
