"""Modelo LLM fake para testes — sem chamadas de rede."""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


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

    @property
    def _llm_type(self) -> str:
        return "fake"
