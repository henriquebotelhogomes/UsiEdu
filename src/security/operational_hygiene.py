"""Guardas reutilizaveis para inventario e logs operacionais."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

REDACTED_VALUE = "[REDACTED]"

_SENSITIVE_FIELD_NAMES = frozenset(
    {
        "apikey",
        "authorization",
        "credential",
        "credentials",
        "email",
        "message",
        "question",
        "answer",
        "content",
        "comment",
        "prompt",
        "query",
        "session",
        "sessionid",
        "user",
        "userid",
        "useremail",
        "jwt",
        "password",
        "secret",
        "token",
    }
)
_SIMULATED_SECRET_ASSIGNMENT = re.compile(
    r"""(?ix)
    (?:"?(?:api[_-]?key|authorization|credential|jwt|password|secret|token)"?)
    \s*[:=]\s*
    (?:"[^"\r\n]+"|'[^'\r\n]+'|[^\s,\}\]]+)
    """
)


def contains_simulated_secret(text: str) -> bool:
    """Detecta uma atribuicao de segredo com valor para autoensaios locais."""
    return _SIMULATED_SECRET_ASSIGNMENT.search(text) is not None


def redact_sensitive_fields(value: Any) -> Any:
    """Copia estruturas de log substituindo valores de campos sensiveis."""
    if isinstance(value, Mapping):
        return {
            key: (
                REDACTED_VALUE
                if _is_sensitive_field_name(str(key))
                else redact_sensitive_fields(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_fields(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive_fields(item) for item in value)
    return value


def _is_sensitive_field_name(name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", name.lower())
    return normalized in _SENSITIVE_FIELD_NAMES or normalized.endswith(
        ("apikey", "password", "token")
    )
