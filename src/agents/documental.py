"""Nó Agente Documental do grafo LangGraph.

Conforme doc 02 seção 3 — integração com retriever + citação obrigatória.
"""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.prompts.documental import DOCUMENTAL_SYSTEM_PROMPT
from src.orchestration.state import AgentState
from src.rag.models import Source

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import RunnableConfig


def make_documental_node(
    agent_llm: BaseChatModel,
    retriever=None,
) -> callable:
    """Factory do nó Agente Documental com LLM e retriever injetados.

    Args:
        agent_llm: Modelo LLM usado para gerar respostas.
        retriever: Retriever RAG híbrido (opcional).

    Returns:
        Função de nó pronta para o StateGraph.
    """
    if not agent_llm:
        msg = "agent_llm não pode ser None"
        raise ValueError(msg)

    async def documental_node(state: AgentState, config: RunnableConfig) -> dict:
        """Nó do Agente Documental.

        Recebe a consulta do usuário, recupera contexto RAG (se disponível)
        e gera resposta com citação das fontes institucionais.
        """
        # Extrai a última mensagem do usuário
        last_message = state["messages"][-1].content if state["messages"] else ""

        # Recupera contexto RAG
        context_text = ""
        retrieved_sources: list[Source] = []

        if retriever:
            try:
                results = retriever.search(last_message, profile=state.get("profile", "staff"))
                context_text = _format_context(results)
                retrieved_sources = [r.source for r in results]
            except Exception:
                context_text = "Nenhum contexto disponível no momento."
        else:
            context_text = "Nenhum contexto disponível no momento."

        # Monta o prompt completo
        context_block = (
            f"{context_text}\n\n## Histórico da conversa\n{_format_messages(state['messages'])}"
        )
        system_prompt = DOCUMENTAL_SYSTEM_PROMPT.format(
            context=context_block,
            messages=_format_messages(state["messages"]),
        )

        llm_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=last_message),
        ]

        response = agent_llm.invoke(llm_messages)
        response_text = (
            response.content.strip() if isinstance(response.content, str) else str(response.content)
        )

        # Constrói resultado
        result = {
            "agent": "documental",
            "response": response_text,
            "sources": retrieved_sources,
            "error": None,
        }

        return {
            "agent_results": {**state.get("agent_results", {}), "documental": result},
            "retrieved_sources": retrieved_sources,
        }

    return documental_node


def _format_context(results: list) -> str:
    """Formata resultados RAG para o prompt."""
    if not results:
        return "Nenhum documento relevante encontrado."

    parts = []
    for i, r in enumerate(results[:5], 1):
        parts.append(
            f"[{i}] Documento: {r.source.document}\n"
            f"    Seção: {r.source.section or 'N/A'}\n"
            f"    Conteúdo: {textwrap.shorten(r.source.excerpt, width=300, placeholder='...')}"
        )
    return "\n\n".join(parts)


def _format_messages(messages: list) -> str:
    """Formata as últimas perguntas do usuário para o prompt.

    Filtra apenas mensagens do usuário para evitar que o agente
    repita respostas anteriores (vazamento de contexto entre turnos).
    """
    from langchain_core.messages import HumanMessage

    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    text_parts = []
    for msg in user_messages[-4:]:
        content = msg.content[:500] if isinstance(msg.content, str) else str(msg.content)[:500]
        text_parts.append(f"Usuário: {content}")
    return "\n".join(text_parts)
