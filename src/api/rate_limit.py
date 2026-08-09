"""Rate limiting das rotas da API (T9.1).

Usa ``slowapi`` com armazenamento em memória (processo único). Limites
configuráveis via variáveis de ambiente:

- ``USIEDU_RATE_CHAT``     (default ``10/minute``) — POST ``/chat`` e
  ``/chat/stream``, por usuário autenticado;
- ``USIEDU_RATE_LOGIN``    (default ``5/minute``)  — POST ``/auth/login``, por IP;
- ``USIEDU_RATE_FEEDBACK`` (default ``30/minute``) — POST ``/feedback``,
  por usuário autenticado.

Chave de limite: e-mail do JWT quando presente, senão o IP do cliente.

Deploy atrás de proxy reverso: :func:`chave_ip` confia no header
``X-Forwarded-For`` (primeiro endereço da lista). O proxy DEVE sobrescrever
esse header com o IP real do cliente; caso contrário, todos os clientes
compartilhariam a mesma chave (IP do proxy) ou um atacante poderia forjar
o header para burlar o limite.
"""

from __future__ import annotations

import os

import jwt
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

LIMITE_CHAT = os.getenv("USIEDU_RATE_CHAT", "10/minute")
LIMITE_LOGIN = os.getenv("USIEDU_RATE_LOGIN", "5/minute")
LIMITE_FEEDBACK = os.getenv("USIEDU_RATE_FEEDBACK", "30/minute")


def chave_ip(request: Request) -> str:
    """Chave por IP do cliente (confia em ``X-Forwarded-For`` quando presente)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "desconhecido"


def chave_usuario(request: Request) -> str:
    """E-mail do JWT quando autenticado; senão, IP do cliente."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        # Import tardio para evitar ciclo (auth importa deste módulo indiretamente)
        from src.api.auth import ALGORITHM, SECRET_KEY

        try:
            payload = jwt.decode(auth[7:], SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if email:
                return str(email)
        except jwt.InvalidTokenError:
            pass
    return chave_ip(request)


# headers_enabled=True: permite injetar ``Retry-After`` na resposta 429
limiter = Limiter(key_func=chave_usuario, headers_enabled=True)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Resposta 429 padronizada do projeto: corpo ``{detail}`` + ``Retry-After``."""
    response = JSONResponse(
        status_code=429,
        content={"detail": f"Limite de requisições excedido: {exc.detail}"},
    )
    # Injeta Retry-After (e headers X-RateLimit-*) com base no limite atingido
    return request.app.state.limiter._inject_headers(response, request.state.view_rate_limit)
