"""Nó de Consolidação do grafo LangGraph.

Conforme PRD v3 (RF3-05, RF3-06) — coleta resultados parciais, executa síntese
cognitiva em perguntas compostas e decide término ou continuação de ciclo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.orchestration.state import AgentState

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

SYNTHESIS_SYSTEM_PROMPT = """Você é o Assistente Virtual UsiEdu.
Sua função é consolidar e sintetizar respostas parciais de múltiplos agentes especialistas
(Acadêmico, Financeiro, Documental) em uma única resposta clara, coesa e amigável para o usuário.

Diretrizes de Síntese:
1. Remova saudações repetitivas ou conflitantes no meio do texto.
2. Integre as informações em seções ou parágrafos lógicos e bem estruturados em Markdown.
3. Mantenha todas as datas, valores, notas, regras e citações exatas fornecidas pelos especialistas.
4. Mantenha o tom profissional, acolhedor e resolutivo.
"""

FORA_DE_ESCOPO_RESPONSE = (
    "Sou o assistente da UsiEdu e atendo dúvidas acadêmicas, financeiras e "
    "institucionais (calendário, notas, faltas, matrícula, boletos, normas e "
    "políticas da universidade). Esse assunto está fora do meu escopo, mas "
    "posso ajudar com algum desses temas?"
)


async def fora_de_escopo_node(state: AgentState) -> dict:
    """Nó de resposta padrão para perguntas fora de escopo (RF-10)."""
    return {
        "messages": [AIMessage(content=FORA_DE_ESCOPO_RESPONSE)],
        "needs_more_info": False,
    }


def make_consolidation_node(synthesis_llm: BaseChatModel | None = None) -> callable:
    """Factory do nó de consolidação com LLM de síntese cognitiva opcional."""

    async def consolidation_node_func(state: AgentState) -> dict:
        """Nó de consolidação: formata ou sintetiza a resposta final do sistema."""
        agent_results = state.get("agent_results", {})
        supervisor_decision = state.get("supervisor_decision")
        cycle_count = state.get("cycle_count", 0)

        if not agent_results:
            return _build_final_response(
                state, "Desculpe, não entendi sua solicitação. Pode reformular?"
            )

        responses = []
        all_sources = []

        for agent_name, result in agent_results.items():
            if result.get("error"):
                responses.append(f"O agente {agent_name} encontrou um erro: {result['error']}")
            elif result.get("response"):
                responses.append(result["response"])
                all_sources.extend(result.get("sources", []))

        # Fast path: único agente -> resposta direta sem custo extra de síntese
        if len(responses) == 1 or synthesis_llm is None:
            consolidated = "\n\n".join(responses)
        else:
            # Multi-agent path: Síntese Cognitiva com LLM (RF3-06)
            user_query = state["messages"][-1].content if state["messages"] else ""
            combined_raw = "\n\n---\n\n".join(
                f"### Resposta Parcial [{agent}]:\n{res.get('response', '')}"
                for agent, res in agent_results.items()
                if res.get("response")
            )
            prompt = (
                f"Pergunta original do usuário:\n{user_query}\n\n"
                f"Respostas parciais dos agentes especialistas:\n{combined_raw}\n\n"
                "Sintetize uma resposta unificada e fluida:"
            )
            try:
                res = await synthesis_llm.ainvoke([
                    SystemMessage(content=SYNTHESIS_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ])
                consolidated = res.content if hasattr(res, "content") else str(res)
            except Exception:
                consolidated = "\n\n".join(responses)

        # Decide se precisa de mais informações
        needs_more_info = False
        intent = (
            supervisor_decision.intent
            if hasattr(supervisor_decision, "intent")
            else (supervisor_decision.get("intent") if supervisor_decision else None)
        )

        if intent == "composta" and len(agent_results) < 2:
            needs_more_info = True
            consolidated += (
                "\n\n**Nota:** Identifiquei que sua pergunta pode envolver "
                "mais de um assunto. Por enquanto, respondi sobre o que "
                "consegui identificar. Se precisar de informações adicionais, "
                "pode perguntar novamente com mais detalhes."
            )

        if cycle_count >= 2:
            needs_more_info = False

        return _build_final_response(
            state,
            consolidated,
            sources=all_sources,
            needs_more_info=needs_more_info,
        )

    return consolidation_node_func


# Instância padrão sem síntese para retrocompatibilidade
consolidation_node = make_consolidation_node(None)


def _build_final_response(
    state: AgentState,
    response_text: str,
    sources: list | None = None,
    needs_more_info: bool = False,
) -> dict:
    """Constrói o dicionário de atualização do estado com a resposta final."""
    message = AIMessage(content=response_text)

    return {
        "messages": [message],
        "needs_more_info": needs_more_info,
        "retrieved_sources": sources or state.get("retrieved_sources", []),
    }


def should_continue(state: AgentState) -> str:
    """Função de roteamento condicional pós-consolidação."""
    if state.get("needs_more_info") and state.get("cycle_count", 0) < 2:
        return "supervisor"

    return "__end__"
