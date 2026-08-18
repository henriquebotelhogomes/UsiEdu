"""Nó Agente Acadêmico do grafo LangGraph.

Conforme doc 02 seção 3 — integração com retriever + tools + citação obrigatória.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.prompts.academico import ACADEMICO_SYSTEM_PROMPT
from src.observability.resilience import stream_with_single_pre_token_retry
from src.orchestration.state import AgentState
from src.rag.models import Source
from src.tools.academico_tools import get_faltas, get_notas

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import RunnableConfig


def make_academico_node(
    agent_llm: BaseChatModel,
    retriever=None,
) -> callable:
    """Factory do nó Agente Acadêmico com LLM e retriever injetados.

    Args:
        agent_llm: Modelo LLM usado para gerar respostas.
        retriever: Retriever RAG híbrido (opcional).

    Returns:
        Função de nó pronta para o StateGraph.
    """
    if not agent_llm:
        msg = "agent_llm não pode ser None"
        raise ValueError(msg)

    async def academico_node(state: AgentState, config: RunnableConfig) -> dict:
        """Nó do Agente Acadêmico.

        Recebe a consulta do usuário, recupera contexto RAG (se disponível),
        consulta ferramentas mockadas (notas, faltas) e gera resposta com citação.
        """
        user_id = state.get("user_id", "")

        # Extrai a última mensagem do usuário
        last_message = state["messages"][-1].content if state["messages"] else ""

        # Recupera contexto RAG
        context_text = ""
        retrieved_sources: list[Source] = []

        if retriever:
            try:
                # Coleção acadêmica contém docs público student;
                # o filtro segue o documento, não o perfil do usuário
                results = retriever.search(last_message, profile="student")
                context_text = _format_context(results)
                retrieved_sources = [r.source for r in results]
            except Exception:
                context_text = "Nenhum contexto disponível no momento."

        else:
            context_text = "Nenhum contexto disponível no momento."

        # Processa ferramentas
        tool_context = await _executar_ferramentas_academicas(user_id, last_message)

        # Monta o prompt completo
        context_block = f"{context_text}\n\n## Dados do aluno (ferramentas)\n{tool_context}"
        system_prompt = ACADEMICO_SYSTEM_PROMPT.format(
            context=context_block,
            messages=_format_messages(state["messages"]),
        )

        llm_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=last_message),
        ]

        # Stream dos tokens do LLM (T7.3): o endpoint /chat/stream captura
        # estes chunks via astream_events e os envia por SSE ao cliente.
        response_parts: list[str] = []
        async for chunk in stream_with_single_pre_token_retry(
            lambda: agent_llm.astream(llm_messages)
        ):
            part = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
            response_parts.append(part)
        response_text = "".join(response_parts).strip()

        # Constrói resultado
        result = {
            "agent": "academico",
            "response": response_text,
            "sources": retrieved_sources,
            "error": None,
        }

        return {
            "agent_results": {**state.get("agent_results", {}), "academico": result},
            "retrieved_sources": retrieved_sources,
        }

    return academico_node


async def _executar_ferramentas_academicas(user_id: str, query: str) -> str:
    """Executa ferramentas mockadas com base na consulta do usuário.

    Extrai o aluno_id do user_id (que é o email) para buscar dados mockados.
    """
    # Mapeia email para aluno_id
    from src.tools.mock_data import USUARIOS_DEMO

    user_info = USUARIOS_DEMO.get(user_id)
    if not user_info:
        return "Usuário não encontrado na base de demonstração."

    aluno_id = user_info.get("aluno_id")
    if not aluno_id:
        return "Perfil staff não possui dados acadêmicos mockados."

    partes = []

    # Verifica se a consulta menciona notas
    if any(
        palavra in query.lower()
        for palavra in ["nota", "notas", "nota", "notas", "boletim", "desempenho"]
    ):
        notas = await get_notas(aluno_id)
        if notas:
            notas_str = "\n".join(f"  - {disc}: {nota}" for disc, nota in notas.items())
            partes.append(f"Notas do aluno:\n{notas_str}")
        else:
            partes.append("Nenhuma nota encontrada.")

    # Verifica se a consulta menciona faltas
    if any(
        palavra in query.lower()
        for palavra in ["falta", "faltas", "presença", "presença", "frequência", "frequencia"]
    ):
        for disciplina in ["calculo-1", "programacao-1"]:
            faltas = await get_faltas(aluno_id, disciplina)
            if faltas:
                total_aulas = 20
                percentual = ((total_aulas - faltas) / total_aulas) * 100
                status = "regular" if percentual >= 75 else "em risco de reprovação"
                partes.append(
                    f"Faltas em {disciplina}: {faltas} de {total_aulas} aulas "
                    f"({percentual:.0f}% frequência) — {status}"
                )

    if not partes:
        return "Nenhuma ferramenta relevante para a consulta."

    return "\n\n".join(partes)


def _format_context(results: list) -> str:
    """Formata resultados RAG para o prompt.

    Trechos longos (até 2400 chars) são mantidos quase na íntegra para
    preservar tabelas e datas; quebras de linha são preservadas.
    """
    if not results:
        return "Nenhum documento relevante encontrado."

    max_chars = 2400
    parts = []
    for i, r in enumerate(results[:5], 1):
        excerpt = r.source.excerpt
        if len(excerpt) > max_chars:
            excerpt = excerpt[:max_chars] + "..."
        parts.append(
            f"[{i}] Documento: {r.source.document}\n"
            f"    Seção: {r.source.section or 'N/A'}\n"
            f"    Conteúdo: {excerpt}"
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
