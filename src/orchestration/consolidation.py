"""Nó de Consolidação do grafo LangGraph.

Conforme doc 02 seção 4 — coleta resultados parciais e decide
se o grafo continua (ciclo) ou finaliza.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from src.orchestration.state import AgentState

CONSOLIDATION_TEMPLATE = """{intro}

{agent_results}

{footer}"""


FOOTER_SEM_INFO = "Caso precise de mais informações, estou aqui para ajudar. 😊"
FOOTER_MORE_INFO = "Para te ajudar melhor, poderia fornecer mais detalhes?"

FORA_DE_ESCOPO_RESPONSE = (
    "Sou o assistente da UsiEdu e atendo dúvidas acadêmicas, financeiras e "
    "institucionais (calendário, notas, faltas, matrícula, boletos, normas e "
    "políticas da universidade). Esse assunto está fora do meu escopo, mas "
    "posso ajudar com algum desses temas?"
)


async def fora_de_escopo_node(state: AgentState) -> dict:
    """Nó de resposta padrão para perguntas fora de escopo (RF-10).

    Nenhum agente é acionado; retorna redirecionamento educado.
    """
    return {
        "messages": [AIMessage(content=FORA_DE_ESCOPO_RESPONSE)],
        "needs_more_info": False,
    }


async def consolidation_node(state: AgentState) -> dict:
    """Nó de consolidação: formata a resposta final do sistema.

    Coleta os resultados de todos os agentes acionados, organiza
    em uma resposta consolidada e decide se precisa de mais informações.

    Regras (RF-11):
    - Se apenas 1 agente respondeu para uma pergunta composta, needs_more_info = True
    - Se algum agente retornou erro, needs_more_info = True
    - Máximo de 2 ciclos antes de responder com o que tem
    """
    agent_results = state.get("agent_results", {})
    supervisor_decision = state.get("supervisor_decision")
    cycle_count = state.get("cycle_count", 0)

    if not agent_results:
        # Nenhum agente respondeu — caso de fora_de_escopo
        return _build_final_response(
            state, "Desculpe, não entendi sua solicitação. Pode reformular?"
        )

    # Monta resposta consolidada
    responses = []
    all_sources = []

    for agent_name, result in agent_results.items():
        if result.get("error"):
            responses.append(f"O agente {agent_name} encontrou um erro: {result['error']}")
        elif result.get("response"):
            responses.append(result["response"])
            all_sources.extend(result.get("sources", []))

    consolidated = "\n\n".join(responses)

    # Decide se precisa de mais informações
    needs_more_info = False
    intent = supervisor_decision.get("intent") if supervisor_decision else None

    if intent == "composta" and len(agent_results) < 2:
        # Pergunta composta mas apenas 1 agente respondeu
        needs_more_info = True
        consolidated += (
            "\n\n**Nota:** Identifiquei que sua pergunta pode envolver "
            "mais de um assunto. Por enquanto, respondi sobre o que "
            "consegui identificar. Se precisar de informações adicionais, "
            "pode perguntar novamente com mais detalhes."
        )

    # Se ultrapassou o limite de ciclos, força resposta
    if cycle_count >= 2:
        needs_more_info = False

    return _build_final_response(
        state,
        consolidated,
        sources=all_sources,
        needs_more_info=needs_more_info,
    )


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
    """Função de roteamento condicional pós-consolidação.

    Retorna:
        "supervisor" se o grafo deve continuar (ciclo).
        "__end__" se o grafo deve finalizar.
    """
    if state.get("needs_more_info") and state.get("cycle_count", 0) < 2:
        return "supervisor"

    return "__end__"
