"""Teste de fluxo completo do grafo com LLM real + RAG (pergunta feriados)."""

import asyncio
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

from src.api.main import _build_retrievers
from src.llm.provider import get_chat_model
from src.orchestration.graph import create_chat_graph


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

    state = {
        "user_id": "carlos@demo.usiedu",
        "profile": "staff",
        "messages": [HumanMessage(content="Quais feriados temos esse ano?")],
        "plan": None,
        "delegations": [],
        "agent_results": {},
        "retrieved_sources": [],
        "needs_more_info": False,
        "cycle_count": 0,
        "supervisor_decision": None,
    }
    config = {"configurable": {"thread_id": "teste-feriados-1"}}

    result = await graph.ainvoke(state, config)
    messages = result.get("messages", [])
    answer = messages[-1].content if messages else ""
    print("=== INTENT ===")
    print(result.get("supervisor_decision", {}).get("intent"))
    print("=== AGENTES ===")
    print(list(result.get("agent_results", {}).keys()))
    print("=== FONTES ===")
    for s in result.get("retrieved_sources", [])[:5]:
        print(f"- {s.document} | {s.section}")
    print("=== RESPOSTA ===")
    print(answer[:1000])


asyncio.run(main())
