"""Camada provider-agnostic de LLM.

Factory `get_chat_model()` que retorna um `BaseChatModel` conforme
a variável de ambiente `USIEDU_LLM_PROVIDER`.

Suporta:
- opencode-go: endpoint OpenAI-compatible (OpenCode Go)
- gemini: stub documentado (langchain-google-vertexai)
- fake: modelo determinístico para testes
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


def get_chat_model(
    provider: str | None = None,
    model_name: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> BaseChatModel:
    """Retorna um modelo de chat conforme o provider configurado.

    Args:
        provider: Nome do provider. Se None, lê de USIEDU_LLM_PROVIDER env.
        model_name: Nome do modelo. Se None, usa o padrão do provider.

    Returns:
        Instância de BaseChatModel pronta para uso.
    """
    provider = provider or os.getenv("USIEDU_LLM_PROVIDER", "opencode-go")

    if provider == "fake":
        from src.llm.fake import FakeChatModel

        return FakeChatModel()

    if provider == "opencode-go":
        return _build_opencode_go(model_name, temperature, max_tokens)

    if provider == "gemini":
        return _build_gemini_stub(model_name)

    msg = f"Provider desconhecido: {provider}. Opções: opencode-go, gemini, fake"
    raise ValueError(msg)


def _build_opencode_go(
    model_name: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> BaseChatModel:
    """Constrói ChatOpenAI apontando para endpoint OpenCode Go."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model_name or os.getenv("USIEDU_ROUTER_MODEL", "deepseek-v4-flash"),
        base_url=os.getenv("OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1"),
        api_key=os.getenv("OPENCODE_GO_API_KEY", ""),
        max_retries=0,
        # Console Go/OpenCode Go exige temperature=1 para alguns modelos
        temperature=1.0 if temperature is None else temperature,
        max_tokens=max_tokens,
        stream_usage=True,
        timeout=float(os.getenv("USIEDU_LLM_TIMEOUT_SECONDS", "120")),
    )


def _build_gemini_stub(model_name: str | None = None) -> BaseChatModel:
    """Constrói ChatVertexAI (Gemini) — stub documentado.

    Nota: Requer langchain-google-vertexai e credenciais GCP configuradas.
    Não usado no piloto — implementado para demonstrar aderência ao ecossistema Google.
    """
    try:
        from langchain_google_vertexai import ChatVertexAI

        return ChatVertexAI(
            model=model_name or "gemini-2.0-flash",
            temperature=0.1,
        )
    except ImportError:
        msg = (
            "Gemini não disponível: instale langchain-google-vertexai "
            "e configure GOOGLE_APPLICATION_CREDENTIALS"
        )
        raise ImportError(msg) from None
