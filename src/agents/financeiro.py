"""Nó Agente Financeiro do grafo LangGraph.

Conforme doc 02 seção 3 — integração com retriever + tools + citação obrigatória.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.prompts.financeiro import FINANCEIRO_SYSTEM_PROMPT
from src.orchestration.state import AgentState
from src.rag.models import Source
from src.tools.financeiro_tools import get_boletos, get_politica_renegociacao, simular_renegociacao

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

    async def financeiro_node(state: AgentState, config: RunnableConfig) -> dict:
        """Nó do Agente Financeiro.

        Recebe a consulta do usuário, recupera contexto RAG (se disponível),
        consulta ferramentas mockadas (boletos, renegociação) e gera resposta.
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
        tool_context = await _executar_ferramentas_financeiras(user_id, last_message)

        # Monta o prompt completo
        context_block = f"{context_text}\n\n## Dados do aluno (ferramentas)\n{tool_context}"
        system_prompt = FINANCEIRO_SYSTEM_PROMPT.format(
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
            "agent": "financeiro",
            "response": response_text,
            "sources": retrieved_sources,
            "error": None,
        }

        return {
            "agent_results": {**state.get("agent_results", {}), "financeiro": result},
            "retrieved_sources": retrieved_sources,
        }

    return financeiro_node


async def _executar_ferramentas_financeiras(user_id: str, query: str) -> str:
    """Executa ferramentas mockadas financeiras com base na consulta do usuário."""
    from src.tools.mock_data import USUARIOS_DEMO

    user_info = USUARIOS_DEMO.get(user_id)
    if not user_info:
        return "Usuário não encontrado na base de demonstração."

    aluno_id = user_info.get("aluno_id")
    if not aluno_id:
        return "Perfil staff não possui dados financeiros mockados."

    partes = []

    # Verifica se a consulta menciona boletos
    if any(
        palavra in query.lower()
        for palavra in ["boleto", "boletos", "mensalidade", "pagamento", "divida", "dívida"]
    ):
        boletos = await get_boletos(aluno_id)
        if boletos:
            boletos_str = "\n".join(
                f"  - {b['id']}: R$ {b['valor']:.2f} (vencimento: {b['vencimento']}, "
                f"status: {b['status']})"
                for b in boletos
            )
            partes.append(f"Boletos do aluno:\n{boletos_str}")
        else:
            partes.append("Nenhum boleto encontrado.")

    # Verifica se a consulta menciona renegociação
    if any(
        palavra in query.lower()
        for palavra in ["renegociar", "renegociação", "negociar", "parcelar", "divida", "dívida"]
    ):
        simulacao = await simular_renegociacao(aluno_id)
        if simulacao.get("possivel"):
            partes.append(
                f"Simulação de renegociação:\n{simulacao['proposta']}\n"
                f"  Condição: {simulacao['condicao']}"
            )
        else:
            partes.append(f"Renegociação: {simulacao['motivo']}")

    # Verifica se a consulta menciona política de renegociação
    if any(
        palavra in query.lower()
        for palavra in ["política", "politica", "renegociação", "renegociacao", "desconto"]
    ):
        politica = await get_politica_renegociacao()
        partes.append(
            f"Política de renegociação vigente:\n"
            f"  - Desconto máximo: {politica['desconto_maximo_percentual']}%\n"
            f"  - Parcelas máximas: {politica['parcelas_maximas']}x\n"
            f"  - Condição: {politica['condicao']}"
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
