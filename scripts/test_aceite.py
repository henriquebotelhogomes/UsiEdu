"""Verificação dos critérios de aceite do doc 04 (seção 5) com LLM real + RAG.

Cenários:
- C1: pergunta composta (acadêmico+financeiro) — Ana (student)
- C2: norma institucional com citação — Carlos (staff)
- C4: pergunta fora de escopo — Ana (student)
- C5: contexto entre turnos no mesmo thread_id — Ana (student)
"""

import asyncio
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

from src.api.main import _build_retrievers
from src.llm.provider import get_chat_model
from src.orchestration.graph import create_chat_graph


def make_state(user_id: str, profile: str, question: str) -> dict:
    return {
        "user_id": user_id,
        "profile": profile,
        "messages": [HumanMessage(content=question)],
        "plan": None,
        "delegations": [],
        "agent_results": {},
        "retrieved_sources": [],
        "needs_more_info": False,
        "cycle_count": 0,
        "supervisor_decision": None,
    }


def print_result(title: str, result: dict) -> None:
    messages = result.get("messages", [])
    answer = messages[-1].content if messages else ""
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")
    print(f"INTENT: {result.get('supervisor_decision', {}).get('intent')}")
    print(f"AGENTES: {list(result.get('agent_results', {}).keys())}")
    fontes = {f"{s.document} | {s.section}" for s in result.get("retrieved_sources", [])}
    for f in sorted(fontes)[:5]:
        print(f"  FONTE: {f}")
    print(f"RESPOSTA:\n{answer[:900]}")


async def main() -> None:
    router_llm = get_chat_model(model_name="deepseek-v4-flash")
    agent_llm = get_chat_model(model_name=os.getenv("USIEDU_AGENT_MODEL", "deepseek-v4-flash"))
    retriever, documental_retriever = _build_retrievers()
    graph = create_chat_graph(
        router_llm=router_llm,
        agent_llm=agent_llm,
        retriever=retriever,
        documental_retriever=documental_retriever,
    )

    # C1 — pergunta composta (Ana)
    state = make_state(
        "ana@demo.usiedu",
        "student",
        "Perdi o prazo de matrícula em Cálculo. Quais são minhas opções e quanto custa o boleto?",
    )
    result = await graph.ainvoke(state, {"configurable": {"thread_id": "aceite-c1"}})
    print_result("C1 — PERGUNTA COMPOSTA (Ana)", result)

    # C2 — norma institucional com citação (Carlos)
    state = make_state(
        "carlos@demo.usiedu",
        "staff",
        "Quais são meus direitos de licença capacitação?",
    )
    result = await graph.ainvoke(state, {"configurable": {"thread_id": "aceite-c2"}})
    print_result("C2 — NORMA INSTITUCIONAL COM CITAÇÃO (Carlos)", result)

    # C4 — fora de escopo (Ana)
    state = make_state("ana@demo.usiedu", "student", "Qual a previsão do tempo hoje em Brasília?")
    result = await graph.ainvoke(state, {"configurable": {"thread_id": "aceite-c4"}})
    print_result("C4 — FORA DE ESCOPO (Ana)", result)

    # C5 — contexto entre turnos (Ana, mesmo thread_id)
    state = make_state(
        "ana@demo.usiedu",
        "student",
        "Oi! Sou a Ana, estudante de Análise e Desenvolvimento de Sistemas.",
    )
    config = {"configurable": {"thread_id": "aceite-c5"}}
    await graph.ainvoke(state, config)
    state2 = make_state("ana@demo.usiedu", "student", "Qual curso eu disse que estou fazendo?")
    result = await graph.ainvoke(state2, config)
    print_result("C5 — CONTEXTO ENTRE TURNOS (Ana)", result)


asyncio.run(main())
