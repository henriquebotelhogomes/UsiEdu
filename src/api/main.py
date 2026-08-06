"""Aplicação FastAPI da UsiEdu.

Conforme doc 09 seção 1 — servidor REST com autenticação JWT e chat.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from src.api.auth import router as auth_router
from src.api.chat import init_graph
from src.api.chat import router as chat_router
from src.llm.provider import get_chat_model
from src.observability.logging import setup_logging
from src.orchestration.graph import create_chat_graph

# Carrega variáveis do .env (se existir) antes de qualquer configuração
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Inicializa e finaliza recursos da aplicação.

    - Configura logging JSON estruturado
    - Cria o grafo LangGraph com os modelos configurados
    - Configura checkpointer SQLite
    """
    # Configura logging
    setup_logging()

    # Obtém modelos conforme variáveis de ambiente
    router_model_name = os.getenv("USIEDU_ROUTER_MODEL", "deepseek-v4-flash")
    agent_model_name = os.getenv("USIEDU_AGENT_MODEL", "deepseek-v4-flash")

    router_llm = get_chat_model(model_name=router_model_name)
    agent_llm = get_chat_model(model_name=agent_model_name)

    # Checkpointer SQLite
    db_path = os.getenv("USIEDU_CHECKPOINTER_DB", "usiedu_checkpoints.db")
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        # Cria o grafo
        graph = create_chat_graph(
            router_llm=router_llm,
            agent_llm=agent_llm,
            financeiro_llm=agent_llm,
            documental_llm=agent_llm,
            retriever=None,  # RAG opcional no piloto
            checkpointer=checkpointer,
        )

        # Injeta o grafo no módulo de chat
        init_graph(graph)

        yield

    # Cleanup: nada necessário por enquanto


def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI."""
    app = FastAPI(
        title="UsiEdu API",
        description="API da plataforma multi-agente de IA conversacional para educação",
        version="0.2.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rotas
    app.include_router(auth_router)
    app.include_router(chat_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.2.0"}

    return app


app = create_app()
