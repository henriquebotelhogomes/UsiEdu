"""Cache semântico do chat (T9.2).

Estratégia em camadas (PRD v2 — T9.2):

1. **Cache exato:** chave = sha256(perfil + pergunta normalizada) → hit imediato.
2. **Cache semântico:** embedding da pergunta (mesmo modelo da ingestão)
   comparado por cosseno com os embeddings cacheados; limiar configurável
   via ``USIEDU_CACHE_SIMILARITY`` (default 0.97).

Armazenamento: tabela SQLite ``chat_cache`` com TTL (default 30 dias,
``USIEDU_CACHE_TTL_DAYS``) e invalidação por ``doc_version`` — sha256 do
``manifest.json`` da base de conhecimento. Entradas gravadas sob uma versão
dos documentos não são servidas nem regravadas após a base mudar.

Política de cache (decisão documentada — recomendação do PRD):
- Somente a **primeira mensagem** da sessão (histórico vazio); sessões com
  contexto prévio nunca usam nem alimentam o cache.
- Somente respostas de intenção ``institucional`` (conhecimento geral da
  base); ``academico``/``financeiro`` podem conter dados pessoais de tools
  e nunca são cacheadas.
- Erros e respostas ``fora_de_escopo`` nunca são cacheadas.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from pathlib import Path

import aiosqlite
import numpy as np

from src.storage.database import database_url, postgres_connection

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS chat_cache (
    key TEXT PRIMARY KEY,
    profile TEXT NOT NULL,
    question TEXT NOT NULL,
    answer_json TEXT NOT NULL,
    embedding BLOB,
    doc_version TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

_CREATE_POSTGRES_TABLE = """
CREATE TABLE IF NOT EXISTS chat_cache (
    key TEXT PRIMARY KEY,
    profile TEXT NOT NULL,
    question TEXT NOT NULL,
    answer_json TEXT NOT NULL,
    embedding BYTEA,
    doc_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
)
"""


def _cache_db_path() -> str:
    return os.getenv("USIEDU_CACHE_DB", "usiedu_cache.db")


def cache_ativo() -> bool:
    """Flag de ativação do cache (env ``USIEDU_CACHE_ENABLED``, default true)."""
    return os.getenv("USIEDU_CACHE_ENABLED", "true").strip().lower() not in (
        "false",
        "0",
        "no",
    )


def _limiar_similaridade() -> float:
    try:
        return float(os.getenv("USIEDU_CACHE_SIMILARITY", "0.97"))
    except ValueError:
        return 0.97


def _ttl_dias() -> int:
    try:
        return int(os.getenv("USIEDU_CACHE_TTL_DAYS", "30"))
    except ValueError:
        return 30


def normalizar_pergunta(texto: str) -> str:
    """Normaliza a pergunta para a chave do cache exato.

    Lowercase, sem acentos e com espaços colapsados — variações triviais de
    digitação caem na mesma chave.
    """
    texto = texto.strip().lower()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", texto)


def chave_cache(profile: str, pergunta_normalizada: str) -> str:
    """Chave do cache exato: sha256(perfil + pergunta normalizada)."""
    return hashlib.sha256(f"{profile}|{pergunta_normalizada}".encode("utf-8")).hexdigest()


def doc_version_atual(manifest_path: str | None = None) -> str:
    """Hash do ``manifest.json`` da base de conhecimento (invalidação).

    Sem manifest disponível retorna vazio: o cache segue operando, mas sob
    uma versão neutra (comportamento documentado e coberto por teste).
    """
    caminho = Path(
        manifest_path or os.getenv("USIEDU_MANIFEST_PATH", "knowledge_base/manifest.json")
    )
    if not caminho.exists():
        return ""
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def similaridade_cosseno(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
    """Similaridade de cosseno entre dois vetores (0.0 se degenerados)."""
    va = np.asarray(a, dtype=np.float64)
    vb = np.asarray(b, dtype=np.float64)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)


class ChatCache:
    """Cache de respostas do chat em SQLite (exato + semântico)."""

    def __init__(self, embedder=None) -> None:
        self._embedder = embedder
        self.hits = 0
        self.misses = 0

    @property
    def embedder(self):
        """Embedder lazy: mesmo modelo da ingestão (não carrega em testes sem uso)."""
        if self._embedder is None:
            from src.rag.embedder import Embedder

            self._embedder = Embedder()
        return self._embedder

    async def lookup(
        self,
        profile: str,
        question: str,
        doc_version: str | None = None,
    ) -> dict | None:
        """Busca no cache: primeiro a chave exata, depois a semântica.

        Retorna ``{"answer": dict, "from_cache": True, "exact": bool,
        "similarity": float}`` ou None. Atualiza os contadores hit/miss.
        """
        if not cache_ativo() or not question.strip():
            return None

        versao = doc_version if doc_version is not None else doc_version_atual()
        chave = chave_cache(profile, normalizar_pergunta(question))
        limite = (datetime.now(UTC) - timedelta(days=_ttl_dias())).isoformat()

        try:
            if database_url():
                result = await self._lookup_postgres(profile, question, versao, chave, limite)
                if result is not None:
                    return result
                self.misses += 1
                logger.info("Cache miss", extra={"cache_hit": False})
                return None
            async with aiosqlite.connect(_cache_db_path()) as db:
                await db.execute(_CREATE_TABLE)

                # Camada 1 — cache exato
                async with db.execute(
                    """
                    SELECT answer_json FROM chat_cache
                    WHERE key = ? AND profile = ? AND doc_version = ? AND created_at > ?
                    """,
                    (chave, profile, versao, limite),
                ) as cursor:
                    row = await cursor.fetchone()
                if row:
                    self.hits += 1
                    logger.info("Cache hit", extra={"cache_hit": True, "exact": True})
                    return {
                        "answer": json.loads(row[0]),
                        "from_cache": True,
                        "exact": True,
                        "similarity": 1.0,
                    }

                # Camada 2 — cache semântico (só perfaz o embedding aqui se necessário)
                async with db.execute(
                    """
                    SELECT embedding, answer_json FROM chat_cache
                    WHERE profile = ? AND doc_version = ? AND created_at > ?
                        AND embedding IS NOT NULL
                    """,
                    (profile, versao, limite),
                ) as cursor:
                    candidatos = await cursor.fetchall()

                if candidatos:
                    query_vec = np.asarray(self.embedder.embed_query(question), dtype=np.float32)
                    melhor_sim, melhor_answer = 0.0, None
                    for emb_blob, answer_json in candidatos:
                        sim = similaridade_cosseno(
                            query_vec, np.frombuffer(emb_blob, dtype=np.float32)
                        )
                        if sim > melhor_sim:
                            melhor_sim, melhor_answer = sim, answer_json
                    if melhor_answer is not None and melhor_sim >= _limiar_similaridade():
                        self.hits += 1
                        logger.info(
                            "Cache hit",
                            extra={"cache_hit": True, "exact": False, "similarity": melhor_sim},
                        )
                        return {
                            "answer": json.loads(melhor_answer),
                            "from_cache": True,
                            "exact": False,
                            "similarity": melhor_sim,
                        }
        except Exception:  # noqa: BLE001 — cache é otimização; falha não derruba o chat
            logger.exception("Falha no lookup do cache; seguindo sem cache.")

        self.misses += 1
        logger.info("Cache miss", extra={"cache_hit": False})
        return None

    async def _lookup_postgres(
        self,
        profile: str,
        question: str,
        version: str,
        key: str,
        limit: str,
    ) -> dict | None:
        """Busca no cache PostgreSQL do piloto publicado."""
        async with postgres_connection() as db:
            await db.execute(_CREATE_POSTGRES_TABLE)
            cursor = await db.execute(
                """
                SELECT answer_json FROM chat_cache
                WHERE key = %s AND profile = %s AND doc_version = %s AND created_at > %s
                """,
                (key, profile, version, limit),
            )
            row = await cursor.fetchone()
            if row:
                self.hits += 1
                logger.info("Cache hit", extra={"cache_hit": True, "exact": True})
                return {
                    "answer": json.loads(row[0]),
                    "from_cache": True,
                    "exact": True,
                    "similarity": 1.0,
                }

            cursor = await db.execute(
                """
                SELECT embedding, answer_json FROM chat_cache
                WHERE profile = %s AND doc_version = %s AND created_at > %s
                    AND embedding IS NOT NULL
                """,
                (profile, version, limit),
            )
            candidates = await cursor.fetchall()

        if not candidates:
            return None
        query_vec = np.asarray(self.embedder.embed_query(question), dtype=np.float32)
        best_similarity, best_answer = 0.0, None
        for embedding, answer_json in candidates:
            similarity = similaridade_cosseno(
                query_vec, np.frombuffer(bytes(embedding), dtype=np.float32)
            )
            if similarity > best_similarity:
                best_similarity, best_answer = similarity, answer_json
        if best_answer is not None and best_similarity >= _limiar_similaridade():
            self.hits += 1
            logger.info(
                "Cache hit",
                extra={"cache_hit": True, "exact": False, "similarity": best_similarity},
            )
            return {
                "answer": json.loads(best_answer),
                "from_cache": True,
                "exact": False,
                "similarity": best_similarity,
            }
        return None

    async def store(
        self,
        profile: str,
        question: str,
        answer: dict,
        doc_version: str | None = None,
    ) -> bool:
        """Grava uma resposta no cache (com embedding para o hit semântico).

        Retorna True se gravou. Falhas são logadas e nunca propagam.
        """
        if not cache_ativo() or not question.strip():
            return False

        versao = doc_version if doc_version is not None else doc_version_atual()
        chave = chave_cache(profile, normalizar_pergunta(question))
        agora = datetime.now(UTC).isoformat()

        try:
            embedding = np.asarray(self.embedder.embed_query(question), dtype=np.float32)
            if database_url():
                await self._store_postgres(profile, question, answer, versao, chave, embedding)
                return True
            async with aiosqlite.connect(_cache_db_path()) as db:
                await db.execute(_CREATE_TABLE)
                await db.execute(
                    """
                    INSERT INTO chat_cache
                        (key, profile, question, answer_json, embedding, doc_version, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        question = excluded.question,
                        answer_json = excluded.answer_json,
                        embedding = excluded.embedding,
                        doc_version = excluded.doc_version,
                        created_at = excluded.created_at
                    """,
                    (
                        chave,
                        profile,
                        question,
                        json.dumps(answer, ensure_ascii=False),
                        embedding.tobytes(),
                        versao,
                        agora,
                    ),
                )
                # Manutenção leve: remove entradas expiradas ou de versões antigas
                await db.execute(
                    "DELETE FROM chat_cache WHERE created_at <= ? OR doc_version != ?",
                    ((datetime.now(UTC) - timedelta(days=_ttl_dias())).isoformat(), versao),
                )
                await db.commit()
            return True
        except Exception:  # noqa: BLE001 — cache é otimização; falha não derruba o chat
            logger.exception("Falha ao gravar no cache.")
            return False

    async def _store_postgres(
        self,
        profile: str,
        question: str,
        answer: dict,
        version: str,
        key: str,
        embedding: np.ndarray,
    ) -> None:
        """Grava e expira entradas no cache PostgreSQL."""
        async with postgres_connection() as db:
            await db.execute(_CREATE_POSTGRES_TABLE)
            await db.execute(
                """
                INSERT INTO chat_cache
                    (key, profile, question, answer_json, embedding, doc_version, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(key) DO UPDATE SET
                    question = excluded.question,
                    answer_json = excluded.answer_json,
                    embedding = excluded.embedding,
                    doc_version = excluded.doc_version,
                    created_at = excluded.created_at
                """,
                (
                    key,
                    profile,
                    question,
                    json.dumps(answer, ensure_ascii=False),
                    embedding.tobytes(),
                    version,
                    datetime.now(UTC),
                ),
            )
            await db.execute(
                "DELETE FROM chat_cache WHERE created_at <= %s OR doc_version != %s",
                (datetime.now(UTC) - timedelta(days=_ttl_dias()), version),
            )

    def stats(self) -> dict:
        """Contadores para ``GET /health`` (T9.2)."""
        return {"cache_hits": self.hits, "cache_misses": self.misses}

    def reset_contadores(self) -> None:
        self.hits = 0
        self.misses = 0


_cache: ChatCache | None = None


def get_chat_cache() -> ChatCache:
    """Singleton do cache (permite injetar embedder fake em testes)."""
    global _cache
    if _cache is None:
        _cache = ChatCache()
    return _cache


def set_chat_cache(cache: ChatCache | None) -> None:
    """Substitui/limpa o singleton (uso exclusivo de testes)."""
    global _cache
    _cache = cache
