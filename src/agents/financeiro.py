"""Nó Agente Financeiro do grafo LangGraph (RF3-03, RF3-04).

Conforme doc 02 seção 3 e PRD v3 — integração com retriever + tools nativas LangChain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.prompts.financeiro import FINANCEIRO_SYSTEM_PROMPT
from src.orchestration.state import AgentState
from src.rag.models import Source
from src.tools.financeiro_tools import (
    FINANCEIRO_TOOLS,
    get_boletos,
    get_politica_renegociacao,
    simular_renegociacao,
)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import RunnableConfig


def make_financeiro_node(
    agent_llm: BaseChatModel,
    retriever=None,
) -> callable:
    """Factory do nó Agente Financeiro com LLM e retriever injetados.

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
            bound_llm = agent_llm.bind_tools(FINANCEIRO_TOOLS)
        except Exception:
            bound_llm = agent_llm

    async def financeiro_node(state: AgentState, config: RunnableConfig) -> dict:
        """Nó do Agente Financeiro."""
        user_id = state.get("user_id", "")
        last_message = state["messages"][-1].content if state["messages"] else ""

        # Recupera contexto RAG com resolução coreferencial de consulta e Self-Querying
        from src.rag.query_rewriter import extract_query_metadata, rewrite_query_for_rag

        search_query = await rewrite_query_for_rag(state.get("messages", []), agent_llm)
        metadata_filters = extract_query_metadata(search_query)

        context_text = ""
        retrieved_sources: list[Source] = []

        if retriever:
            try:
                results = retriever.search(
                    search_query, profile="student", metadata_filters=metadata_filters
                )
                context_text = _format_context(results)
                retrieved_sources = [r.source for r in results]
            except Exception:
                context_text = "Nenhum contexto disponível no momento."
        else:
            context_text = "Nenhum contexto disponível no momento."

        # Processa ferramentas considerando histórico recente de intenção
        combined_query = " ".join(
            m.content
            for m in state["messages"][-3:]
            if hasattr(m, "content") and isinstance(m.content, str)
        )
        tool_context = await _executar_ferramentas_financeiras(user_id, combined_query)

        # Monta prompt completo
        from src.orchestration.context import get_system_context

        context_block = f"{context_text}\n\n## Dados do aluno (ferramentas)\n{tool_context}"
        system_prompt = FINANCEIRO_SYSTEM_PROMPT.format(
            system_context=get_system_context(profile="student"),
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
            "agent": "financeiro",
            "response": response_text,
            "sources": retrieved_sources,
            "error": None,
        }

        return {
            "agent_results": {"financeiro": result},
            "retrieved_sources": retrieved_sources,
        }

    return financeiro_node


async def _executar_ferramentas_financeiras(user_id: str, query: str) -> str:
    """Executa as ferramentas financeiras pertinentes à consulta."""
    from src.tools.mock_data import USUARIOS_DEMO

    usuario = USUARIOS_DEMO.get(user_id)
    if not usuario:
        return "Usuário não encontrado na base de dados."

    if usuario.get("profile") != "student":
        return "Consulta financeira disponível apenas para estudantes."

    aluno_id = usuario.get("aluno_id")
    if not aluno_id:
        return "ID de aluno não vinculado ao usuário."

    partes = []

    # Consulta boletos
    if any(
        palavra in query.lower()
        for palavra in [
            "boleto",
            "boletos",
            "mensalidade",
            "mensalidades",
            "pagamento",
            "pagamentos",
            "vencimento",
            "vencimentos",
            "débito",
            "débitos",
            "debito",
            "debitos",
            "pendência",
            "pendencia",
            "financeiro",
        ]
    ):
        boletos = await get_boletos(aluno_id)
        if boletos:
            boletos_str = "\n".join(
                f"  - Boleto {b['id']}: R$ {b['valor']:.2f} "
                f"(venc: {b['vencimento']}) — status: {b['status']}"
                for b in boletos
            )
            partes.append(f"Boletos do aluno:\n{boletos_str}")
        else:
            partes.append("Nenhum boleto encontrado.")

    # Simulação de renegociação
    if any(
        palavra in query.lower()
        for palavra in [
            "renegociar",
            "renegociação",
            "renegociacao",
            "parcelar",
            "parcelamento",
            "acordo",
            "desconto",
        ]
    ):
        simulacao = await simular_renegociacao(aluno_id)
        if simulacao.get("possivel"):
            partes.append(
                f"Simulação de renegociação:\n"
                f"  - Valor original: R$ {simulacao['valor_original']:.2f}\n"
                f"  - Desconto: {simulacao['desconto_aplicado']}\n"
                f"  - Valor com desconto: R$ {simulacao['valor_com_desconto']:.2f}\n"
                f"  - Parcelamento: {simulacao['proposta']}\n"
                f"  - Condição: {simulacao['condicao']}"
            )
        else:
            partes.append(f"Renegociação: {simulacao.get('motivo')}")

    # Política de renegociação geral
    if any(
        palavra in query.lower()
        for palavra in ["política", "politica", "regras", "como funciona a renegociação"]
    ):
        politica = await get_politica_renegociacao()
        partes.append(
            f"Política de renegociação:\n"
            f"  - Desconto máximo: {politica['desconto_maximo_percentual']}%\n"
            f"  - Parcelas máximas: {politica['parcelas_maximas']}x\n"
            f"  - Condição: {politica['condicao']}"
        )

    if not partes:
        return "Nenhuma ferramenta relevante para a consulta."

    return "\n\n".join(partes)


def _format_context(results: list) -> str:
    """Formata resultados RAG para o prompt com mitigação de 'Lost in the Middle'."""
    if not results:
        return "Nenhum documento relevante encontrado."

    from src.rag.retriever import reorder_context

    # Reordena chunks para [1º, 3º, 5º, 4º, 2º]
    reordered_results = reorder_context(results[:5])

    max_chars = 2400
    parts = []
    for i, r in enumerate(reordered_results, 1):
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
    """Formata as últimas perguntas do usuário para o prompt com poda de tokens (trim_messages)."""
    from langchain_core.messages import HumanMessage, trim_messages

    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    trimmed = trim_messages(
        user_messages,
        max_tokens=2000,
        token_counter=len,
        strategy="last",
        start_on="human",
    )
    text_parts = []
    for msg in trimmed[-4:]:
        content = msg.content[:500] if isinstance(msg.content, str) else str(msg.content)[:500]
        text_parts.append(f"Usuário: {content}")
    return "\n".join(text_parts)
