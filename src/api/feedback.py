"""Endpoint de feedback humano (human-on-the-loop).

Registra avaliações 👍/👎 das respostas do chat em SQLite e, quando o
tracing está ativo, anexa o feedback ao trace correspondente no LangSmith
(run_id = message_id), fechando o ciclo de avaliação contínua.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime

import aiosqlite
from fastapi import APIRouter, Depends

from src.api.auth import get_current_user
from src.api.schemas import (
    ErrorResponse,
    FeedbackRequest,
    FeedbackResponse,
    FeedbackStats,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    rating TEXT NOT NULL CHECK (rating IN ('up', 'down')),
    comment TEXT,
    user_email TEXT NOT NULL,
    profile TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


def _db_path() -> str:
    return os.getenv("USIEDU_FEEDBACK_DB", "usiedu_feedback.db")


def _envia_feedback_langsmith(message_id: str, rating: str, comment: str | None) -> None:
    """Anexa o feedback ao trace no LangSmith (melhor esforço)."""
    try:
        from langsmith import Client

        Client().create_feedback(
            run_id=uuid.UUID(message_id),
            key="user-feedback",
            score=1.0 if rating == "up" else 0.0,
            comment=comment,
        )
    except Exception:  # noqa: BLE001 — feedback local é a fonte primária
        logger.debug("LangSmith indisponível; feedback mantido apenas em SQLite.")


@router.post(
    "",
    response_model=FeedbackResponse,
    responses={401: {"model": ErrorResponse}},
)
async def registrar_feedback(
    request: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
) -> FeedbackResponse:
    """Registra avaliação 👍/👎 de uma resposta do chat.

    Requer autenticação JWT (401 sem token válido).
    """
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(_CREATE_TABLE)
        cursor = await db.execute(
            """
            INSERT INTO feedback
                (session_id, message_id, rating, comment, user_email, profile, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.session_id,
                request.message_id,
                request.rating,
                request.comment,
                current_user["email"],
                current_user["profile"],
                datetime.now(UTC).isoformat(),
            ),
        )
        await db.commit()
        feedback_id = cursor.lastrowid

    _envia_feedback_langsmith(request.message_id, request.rating, request.comment)

    logger.info(
        "Feedback registrado",
        extra={
            "feedback_id": feedback_id,
            "message_id": request.message_id,
            "rating": request.rating,
            "user": current_user["email"],
        },
    )
    return FeedbackResponse(feedback_id=feedback_id or 0)


@router.get(
    "/stats",
    response_model=FeedbackStats,
    responses={401: {"model": ErrorResponse}},
)
async def stats_feedback(
    current_user: dict = Depends(get_current_user),
) -> FeedbackStats:
    """Retorna métricas agregadas de satisfação.

    Requer autenticação JWT (401 sem token válido).
    """
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(_CREATE_TABLE)
        async with db.execute("SELECT rating, COUNT(*) FROM feedback GROUP BY rating") as cursor:
            counts = {row[0]: row[1] for row in await cursor.fetchall()}

    up = counts.get("up", 0)
    down = counts.get("down", 0)
    total = up + down
    return FeedbackStats(
        total=total,
        up=up,
        down=down,
        satisfaction=round(up / total, 4) if total else 0.0,
    )
