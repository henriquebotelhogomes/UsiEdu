"""Endpoint de feedback humano (human-on-the-loop).

Registra avaliações 👍/👎 das respostas do chat em SQLite e, quando o
tracing está ativo, anexa o feedback ao trace correspondente no LangSmith
(run_id = message_id), fechando o ciclo de avaliação contínua.
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import UTC, datetime

import aiosqlite
from fastapi import APIRouter, Depends, Query, Request, Response

from src.api.auth import get_current_user
from src.api.rate_limit import LIMITE_FEEDBACK, limiter
from src.api.schemas import (
    ErrorResponse,
    FeedbackRecentItem,
    FeedbackRecentResponse,
    FeedbackRequest,
    FeedbackResponse,
    FeedbackStats,
)
from src.storage.database import database_url, postgres_connection

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

_CREATE_POSTGRES_TABLE = """
CREATE TABLE IF NOT EXISTS feedback (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    rating TEXT NOT NULL CHECK (rating IN ('up', 'down')),
    comment TEXT,
    user_email TEXT NOT NULL,
    profile TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
)
"""


def _db_path() -> str:
    return os.getenv("USIEDU_FEEDBACK_DB", "usiedu_feedback.db")


def _serializar_created_at(value: str | datetime) -> str:
    """Normaliza TIMESTAMPTZ do PostgreSQL ao contrato ISO 8601 da API."""
    return value.isoformat() if isinstance(value, datetime) else value


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
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
@limiter.limit(LIMITE_FEEDBACK)
async def registrar_feedback(
    request: Request,
    payload: FeedbackRequest,
    response: Response,
    current_user: dict = Depends(get_current_user),
) -> FeedbackResponse:
    """Registra avaliação 👍/👎 de uma resposta do chat.

    Requer autenticação JWT (401 sem token válido). Limitado por usuário
    (T9.1); o parâmetro `request` é o starlette Request exigido pelo slowapi.
    """
    if database_url():
        async with postgres_connection() as db:
            await db.execute(_CREATE_POSTGRES_TABLE)
            cursor = await db.execute(
                """
                INSERT INTO feedback
                    (session_id, message_id, rating, comment, user_email, profile, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    payload.session_id,
                    payload.message_id,
                    payload.rating,
                    payload.comment,
                    current_user["email"],
                    current_user["profile"],
                    datetime.now(UTC),
                ),
            )
            feedback_id = (await cursor.fetchone())[0]
    else:
        async with aiosqlite.connect(_db_path()) as db:
            await db.execute(_CREATE_TABLE)
            cursor = await db.execute(
                """
                INSERT INTO feedback
                    (session_id, message_id, rating, comment, user_email, profile, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.session_id,
                    payload.message_id,
                    payload.rating,
                    payload.comment,
                    current_user["email"],
                    current_user["profile"],
                    datetime.now(UTC).isoformat(),
                ),
            )
            await db.commit()
            feedback_id = cursor.lastrowid

    _envia_feedback_langsmith(payload.message_id, payload.rating, payload.comment)

    logger.info(
        "Feedback registrado",
        extra={
            "feedback_id": feedback_id,
            "message_id": payload.message_id,
            "rating": payload.rating,
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
    if database_url():
        async with postgres_connection() as db:
            await db.execute(_CREATE_POSTGRES_TABLE)
            cursor = await db.execute("SELECT rating, COUNT(*) FROM feedback GROUP BY rating")
            counts = {row[0]: row[1] for row in await cursor.fetchall()}
    else:
        async with aiosqlite.connect(_db_path()) as db:
            await db.execute(_CREATE_TABLE)
            async with db.execute(
                "SELECT rating, COUNT(*) FROM feedback GROUP BY rating"
            ) as cursor:
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


@router.get(
    "/recent",
    response_model=FeedbackRecentResponse,
    responses={401: {"model": ErrorResponse}},
)
async def recent_feedback(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100, description="Máximo de registros"),
) -> FeedbackRecentResponse:
    """Retorna os feedbacks mais recentes (T8.2 — página /insights).

    O `message_id` cru não é exposto: retorna apenas um hash truncado
    (sha256, 8 caracteres) para referência sem vazar UUIDs de run.
    Requer autenticação JWT (401 sem token válido).
    """
    if database_url():
        async with postgres_connection() as db:
            await db.execute(_CREATE_POSTGRES_TABLE)
            cursor = await db.execute(
                """
                SELECT rating, comment, profile, created_at, message_id
                FROM feedback
                ORDER BY id DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
    else:
        async with aiosqlite.connect(_db_path()) as db:
            await db.execute(_CREATE_TABLE)
            async with db.execute(
                """
                SELECT rating, comment, profile, created_at, message_id
                FROM feedback
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()

    items = [
        FeedbackRecentItem(
            rating=row[0],
            comment=row[1],
            profile=row[2],
            created_at=_serializar_created_at(row[3]),
            message_ref=hashlib.sha256(row[4].encode("utf-8")).hexdigest()[:8],
        )
        for row in rows
    ]
    return FeedbackRecentResponse(items=items)
