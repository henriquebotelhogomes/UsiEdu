"""Nó Agente Acadêmico do grafo LangGraph (RF3-03, RF3-04).

Conforme doc 02 seção 3 e PRD v3 — integração com retriever + tools nativas LangChain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.prompts.academico import ACADEMICO_SYSTEM_PROMPT
from src.orchestration.state import AgentState
from src.rag.models import Source
from src.tools.academico_tools import ACADEMICO_TOOLS, get_faltas, get_notas

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

    # Vincula ferramentas nativas ao modelo se suportado (RF3-04)
    bound_llm = agent_llm
    if hasattr(agent_llm, "bind_tools"):
        try:
            bound_llm = agent_llm.bind_tools(ACADEMICO_TOOLS)
        except Exception:
            bound_llm = agent_llm

    async def academico_node(state: AgentState, config: RunnableConfig) -> dict:
        """Nó do Agente Acadêmico."""
        user_id = state.get("user_id", "")
        last_message = state["messages"][-1].content if state["messages"] else ""

        # Recupera contexto RAG
        context_text = ""
        retrieved_sources: list[Source] = []

        if retriever:
            try:
                results = retriever.search(last_message, profile="student")
                context_text = _format_context(results)
                retrieved_sources = [r.source for r in results]
            except Exception:
                context_text = "Nenhum contexto disponível no momento."
        else:
            context_text = "Nenhum contexto disponível no momento."

        # Processa ferramentas
        tool_context = await _executar_ferramentas_academicas(user_id, last_message)

        # Monta prompt completo
        context_block = f"{context_text}\n\n## Dados do aluno (ferramentas)\n{tool_context}"
        system_prompt = ACADEMICO_SYSTEM_PROMPT.format(
            context=context_block,
            messages=_format_messages(state["messages"]),
        )

        llm_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=last_message),
        ]

        # Streaming de tokens do LLM (suporta ferramentas vinculadas)
        response_parts: list[str] = []
        async for chunk in bound_llm.astream(llm_messages):
            part = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
            response_parts.append(part)
        response_text = "".join(response_parts).strip()

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
    """Executa as ferramentas acadêmicas pertinentes à consulta."""
    from src.tools.mock_data import USUARIOS_DEMO

    usuario = USUARIOS_DEMO.get(user_id)
    if not usuario:
        return "Usuário não encontrado na base de dados."

    if usuario.get("profile") != "student":
        return "Perfil de funcionário não possui dados acadêmicos (notas/faltas)."

    aluno_id = usuario.get("aluno_id")
    if not aluno_id:
        return "ID de aluno não vinculado ao usuário."

    partes = []

    # Verifica se a consulta menciona notas
    if any(palavra in query.lower() for palavra in ["nota", "notas", "boletim", "desempenho"]):
        notas = await get_notas(aluno_id)
        if notas:
            notas_str = "\n".join(f"  - {disc}: {nota}" for disc, nota in notas.items())
            partes.append(f"Notas do aluno:\n{notas_str}")
        else:
            partes.append("Nenhuma nota encontrada.")

    # Verifica se a consulta menciona faltas
    if any(
        palavra in query.lower()
        for palavra in ["falta", "faltas", "presença", "frequência", "frequencia"]
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
    """Formata resultados RAG para o prompt."""
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
    """Formata as últimas perguntas do usuário para o prompt."""
    from langchain_core.messages import HumanMessage

    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    text_parts = []
    for msg in user_messages[-4:]:
        content = msg.content[:500] if isinstance(msg.content, str) else str(msg.content)[:500]
        text_parts.append(f"Usuário: {content}")
    return "\n".join(text_parts)
