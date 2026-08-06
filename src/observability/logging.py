"""Logging JSON estruturado com trace_id.

Conforme RF-31 — logs estruturados em JSON com trace_id para correlação.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

TRACE_ID_CTX_KEY = "trace_id"


class JSONFormatter(logging.Formatter):
    """Formatter que produz logs em JSON estruturado.

    Inclui campos: timestamp, level, logger, message, trace_id,
    e quaisquer campos extras passados no extra= dict.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Adiciona trace_id se presente no record
        if hasattr(record, TRACE_ID_CTX_KEY):
            log_entry[TRACE_ID_CTX_KEY] = getattr(record, TRACE_ID_CTX_KEY)

        # Adiciona campos extras fornecidos via extra={}
        for key, value in record.__dict__.items():
            if key not in (
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "message",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
                TRACE_ID_CTX_KEY,
            ):
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False)


def generate_trace_id() -> str:
    """Gera um trace_id único para correlação de logs."""
    return uuid.uuid4().hex[:16]


def setup_logging(*, level: str = "INFO") -> None:
    """Configura o logging global com formato JSON.

    Args:
        level: Nível de log (DEBUG, INFO, WARNING, ERROR).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove handlers existentes para evitar duplicatas
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Ajusta loggers barulhentos de bibliotecas
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
