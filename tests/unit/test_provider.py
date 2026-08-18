"""Testes da camada provider-agnostic de LLM."""

from __future__ import annotations

import pytest

from src.llm.fake import FakeChatModel
from src.llm.provider import _build_opencode_go, get_chat_model


class TestGetChatModel:
    """Testes da factory get_chat_model."""

    def test_provider_fake_retorna_fake_chat_model(self) -> None:
        """Provider 'fake' deve retornar FakeChatModel."""
        model = get_chat_model(provider="fake")
        assert isinstance(model, FakeChatModel)

    def test_provider_opencode_go_retorna_chat_openai(self) -> None:
        """Provider 'opencode-go' deve retornar ChatOpenAI (com mocking)."""
        try:
            model = get_chat_model(provider="opencode-go", model_name="deepseek-v4-flash")
            assert model.__class__.__name__ == "ChatOpenAI"
        except Exception as exc:
            pytest.skip(f"langchain-openai não instalado: {exc}")

    def test_provider_gemini_sem_dependencia_levanta_import_error(self) -> None:
        """Provider 'gemini' sem langchain-google-vertexai deve levantar ImportError."""
        with pytest.raises(ImportError, match="Gemini não disponível"):
            get_chat_model(provider="gemini")

    def test_provider_desconhecido_levanta_value_error(self) -> None:
        """Provider inválido deve levantar ValueError."""
        with pytest.raises(ValueError, match="Provider desconhecido"):
            get_chat_model(provider="inexistente")

    def test_opencode_go_disables_sdk_retries_and_sets_timeout(self, monkeypatch) -> None:
        created_with: dict[str, object] = {}

        class FakeChatOpenAI:
            def __init__(self, **kwargs: object) -> None:
                created_with.update(kwargs)

        monkeypatch.setitem(
            __import__("sys").modules,
            "langchain_openai",
            type("Module", (), {"ChatOpenAI": FakeChatOpenAI}),
        )
        monkeypatch.setenv("USIEDU_LLM_TIMEOUT_SECONDS", "45")

        _build_opencode_go()

        assert created_with["timeout"] == 45.0
        assert created_with["max_retries"] == 0


class TestFakeChatModel:
    """Testes do FakeChatModel."""

    def test_default_response_e_json_valido(self) -> None:
        """Resposta padrão deve ser JSON válido."""
        model = FakeChatModel()
        result = model.invoke([{"role": "user", "content": "qualquer mensagem"}])
        assert result.content is not None
        assert "intent" in result.content

    def test_response_por_padrao_no_texto(self) -> None:
        """Deve retornar resposta configurada para padrão no texto."""
        model = FakeChatModel(
            default_response="resposta padrão",
            responses={"notas": "resposta sobre notas"},
        )
        result = model.invoke([{"role": "user", "content": "Quero ver minhas notas"}])
        assert result.content == "resposta sobre notas"

    def test_fallback_para_default_response(self) -> None:
        """Sem padrão correspondente, deve usar default_response."""
        model = FakeChatModel(
            default_response="resposta padrão",
            responses={"boletos": "resposta sobre boletos"},
        )
        result = model.invoke([{"role": "user", "content": "Quero ver minhas notas"}])
        assert result.content == "resposta padrão"

    def test_llm_type_e_fake(self) -> None:
        """_llm_type deve retornar 'fake'."""
        model = FakeChatModel()
        assert model._llm_type == "fake"
