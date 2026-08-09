"""Modelo LLM fake para testes — sem chamadas de rede."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult


class FakeChatModel(BaseChatModel):
    """Modelo LLM determinístico para testes.

    Retorna respostas predefinidas baseadas em padrões no texto da mensagem.
    Não faz nenhuma chamada de rede — ideal para testar o grafo LangGraph.
    """

    responses: dict[str, str] = {}
    default_response: str = '{"intent": "academico", "plan": null, "reasoning": "teste fake"}'

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Gera resposta determinística baseada no conteúdo da mensagem."""
        last_message = messages[-1].content if messages else ""

        # Procura por padrões nas respostas configuradas
        response_text = self.default_response
        for pattern, response in self.responses.items():
            if pattern.lower() in last_message.lower():
                response_text = response
                break

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response_text))])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ):
        """Simula streaming dividindo a resposta em blocos de palavras.

        Garante que `astream_events` emita eventos `on_chat_model_stream`
        nos testes do endpoint de streaming (T7.3).
        """
        result = self._generate(messages, stop=stop, **kwargs)
        text = result.generations[0].message.content
        for piece in _split_for_streaming(text):
            yield ChatGenerationChunk(message=AIMessageChunk(content=piece))

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ):
        """Versão assíncrona do streaming fake (T7.3)."""
        for chunk in self._stream(messages, stop=stop, **kwargs):
            yield chunk

    @property
    def _llm_type(self) -> str:
        return "fake"


def _split_for_streaming(text: str) -> list[str]:
    """Divide o texto em blocos de até 4 palavras preservando os separadores.

    A concatenação dos blocos reproduz o texto original exatamente.
    """
    tokens = re.findall(r"\S+\s*", text)
    if not tokens:
        return [text] if text else []
    return ["".join(tokens[i : i + 4]) for i in range(0, len(tokens), 4)]
