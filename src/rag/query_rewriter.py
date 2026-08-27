"""Módulo de Reescrita de Consultas e Resolução Coreferencial para RAG.

Padrão Enterprise: transforma perguntas com pronomes ou elipses em diálogos multi-turno
(ex: 'E qual o prazo final para solicitar ele?') em consultas de busca autônomas
(ex: 'Qual o prazo final para solicitar o trancamento de matrícula no semestre 2026.2?').
"""

from __future__ import annotations

# ruff: noqa: E501  (linhas longas intencionais: conteúdo do prompt)
import logging
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AnyMessage

logger = logging.getLogger(__name__)

QUERY_REWRITER_SYSTEM_PROMPT = """Você é um especialista em recuperação de informação (RAG) da plataforma UsiEdu.

Sua tarefa é analisar o histórico recente da conversa e a última pergunta do usuário para REESCREVER a última pergunta como uma consulta de busca autônoma (self-contained), substituindo pronomes (ex: "ele", "disso", "aquilo", "essa regra"), termos implícitos ou elipses pelo seu contexto explícito.

## Regras Obrigatórias:
1. Se a última pergunta já for completa e auto-suficiente, retorne-a EXATAMENTE como está.
2. Não responda à pergunta, apenas reescreva a consulta de busca.
3. Preserve termos técnicos, siglas, códigos e números de normas (ex: "trancamento de matrícula", "2026.2", "bol-001").
4. Responda APENAS com o texto da consulta reescrita, sem aspas, explicações ou preâmbulos.
"""


def _format_recent_history(messages: list[AnyMessage], max_turns: int = 3) -> str:
    """Formata os últimos turnos da conversa para o prompt de reescrita."""
    recent = messages[-(max_turns * 2) :]
    lines = []
    for msg in recent[:-1]:  # Exclui a última mensagem, que é a query atual
        role = "Usuário" if isinstance(msg, HumanMessage) else "Assistente"
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        lines.append(f"{role}: {content[:300]}")
    return "\n".join(lines)


async def rewrite_query_for_rag(
    messages: list[AnyMessage],
    llm: BaseChatModel | None = None,
) -> str:
    """Reescreve a última mensagem do usuário para consulta otimizada de RAG.

    Args:
        messages: Lista completa de mensagens da sessão no estado do agente.
        llm: Modelo LLM para reescrita contextual (opcional).

    Returns:
        String da consulta de busca autônoma e resolvida.
    """
    if not messages:
        return ""

    last_msg = messages[-1]
    raw_query = last_msg.content if isinstance(last_msg.content, str) else str(last_msg.content)
    raw_query = raw_query.strip()

    # Fast-path: Primeiro turno da conversa não possui histórico anterior para resolver
    if len(messages) <= 1 or not llm:
        return raw_query

    # Fast-path: Se o LLM não tem método de invocação ou se a query for muito curta / vazia
    if not hasattr(llm, "ainvoke"):
        return raw_query

    history_text = _format_recent_history(messages)
    if not history_text:
        return raw_query

    prompt_messages = [
        SystemMessage(content=QUERY_REWRITER_SYSTEM_PROMPT),
        HumanMessage(
            content=f"## Histórico recente:\n{history_text}\n\n## Última pergunta do usuário a ser reescrita:\n{raw_query}"
        ),
    ]

    try:
        response = await llm.ainvoke(prompt_messages)
        rewritten = response.content if isinstance(response.content, str) else str(response.content)
        rewritten = rewritten.strip().strip('"').strip("'")
        if rewritten:
            logger.info("Query reescrita para RAG: '%s' -> '%s'", raw_query, rewritten)
            return rewritten
    except Exception as exc:
        logger.warning("Falha ao reescrever query com LLM (%s); usando query original", exc)

    return raw_query
