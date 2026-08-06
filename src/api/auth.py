"""Módulo de autenticação JWT da API.

Conforme doc 09 seção 3 — login com JWT assinado.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.schemas import ErrorResponse, LoginRequest, LoginResponse
from src.tools.mock_data import USUARIOS_DEMO

if TYPE_CHECKING:
    pass

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={401: {"model": ErrorResponse}},
)
async def login(request: LoginRequest) -> LoginResponse:
    """Autentica usuário e retorna token JWT."""
    result = autenticar_usuario(request.email, request.password)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos",
        )
    return result


# Configuração JWT
SECRET_KEY = os.getenv("USIEDU_JWT_SECRET", "chave-dev-piloto-nao-usar-em-producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer(auto_error=False)


def autenticar_usuario(email: str, password: str) -> LoginResponse | None:
    """Autentica usuário contra base mockada.

    Retorna LoginResponse se credenciais forem válidas, None caso contrário.
    """

    user = USUARIOS_DEMO.get(email)
    if not user or user["password"] != password:
        return None

    access_token = _criar_token(email, user["profile"])

    return LoginResponse(
        access_token=access_token,
        profile=user["profile"],
        display_name=user["display_name"],
    )


def _criar_token(email: str, profile: str) -> str:
    """Cria um token JWT para o usuário."""
    payload = {
        "sub": email,
        "profile": profile,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Dependency: extrai e valida o usuário do token JWT.

    Retorna dict com email e profile do usuário autenticado.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        profile: str = payload.get("profile")

        if email is None or profile is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: payload incompleto",
            )

        return {"email": email, "profile": profile}

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
