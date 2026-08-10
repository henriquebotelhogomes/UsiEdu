"""Aplicação FastAPI da UsiEdu.

Conforme doc 09 seção 1 — servidor REST com autenticação JWT e chat.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from slowapi.errors import RateLimitExceeded

from src.api.auth import router as auth_router
from src.api.chat import init_graph
from src.api.chat import router as chat_router
from src.api.chat_stream import router as chat_stream_router
from src.api.feedback import router as feedback_router
from src.api.rate_limit import limiter, rate_limit_exceeded_handler
from src.llm.provider import get_chat_model
from src.observability.logging import setup_logging
from src.orchestration.graph import create_chat_graph
from src.rag.cache import get_chat_cache

# Carrega variáveis do .env (se existir) antes de qualquer configuração
load_dotenv()

logger = logging.getLogger(__name__)


def get_cors_origins() -> list[str]:
    """Retorna as origens permitidas pelo CORS, configuráveis por ambiente.

    Em produção o frontend e a API compartilham a mesma origem por meio do
    proxy nginx; ainda assim, a lista explícita evita aceitar origens
    arbitrárias junto a credenciais.
    """
    configured = os.getenv("USIEDU_CORS_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return ["http://localhost:5173", "http://localhost:5174"]


def _build_retrievers():
    """Cria os retrievers RAG (acadêmico e institucional).

    Retorna (retriever_academico, retriever_institucional).
    Se o Qdrant estiver indisponível, retorna (None, None) e a API
    segue operando sem RAG.
    """
    try:
        from qdrant_client import QdrantClient

        from src.rag.embedder import Embedder
        from src.rag.reranker import Reranker
        from src.rag.retriever import HybridRetriever

        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        client = QdrantClient(qdrant_url)
        embedder = Embedder()

        try:
            reranker: Reranker | None = Reranker()
        except Exception:
            logger.warning("Reranker indisponível; seguindo sem reranking.")
            reranker = None

        academico = HybridRetriever(
            client=client,
            embedder=embedder,
            reranker=reranker,
            collection_name="academico",
        )
        institucional = HybridRetriever(
            client=client,
            embedder=embedder,
            reranker=reranker,
            collection_name="institucional",
        )
        academico.build_bm25_index()
        institucional.build_bm25_index()
        logger.info("Retrievers RAG inicializados (academico + institucional).")
        return academico, institucional
    except Exception:
        logger.exception("Qdrant indisponível; API seguirá sem RAG.")
        return None, None


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

    # Retrievers RAG (acadêmico e institucional)
    retriever, documental_retriever = _build_retrievers()

    # Checkpointer SQLite
    db_path = os.getenv("USIEDU_CHECKPOINTER_DB", "usiedu_checkpoints.db")
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        # Cria o grafo
        graph = create_chat_graph(
            router_llm=router_llm,
            agent_llm=agent_llm,
            financeiro_llm=agent_llm,
            documental_llm=agent_llm,
            retriever=retriever,
            documental_retriever=documental_retriever,
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
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting (T9.1): handler 429 padronizado ({detail} + Retry-After)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Rotas
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(chat_stream_router)
    app.include_router(feedback_router)

    @app.get("/health")
    async def health():
        # Contadores do cache semântico (T9.2)
        return {"status": "ok", "version": "0.2.0", **get_chat_cache().stats()}

    return app


app = create_app()
