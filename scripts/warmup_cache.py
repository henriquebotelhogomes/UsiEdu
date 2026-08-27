"""Script de Pré-Aquecimento (Warmup) do Cache Semântico (T9.2).

Padrão Enterprise: Popula o cache vetorial com o catálogo canônico de perguntas
e respostas frequentes no momento do deploy ou inicialização da aplicação,
garantindo respostas em <15ms a custo zero de tokens desde a primeira requisição.

Uso CLI:
    python scripts/warmup_cache.py [--profile all|student|staff] [--clear-first] [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

# Adiciona a raiz do projeto ao PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.rag.cache import (  # noqa: E402
    _CREATE_POSTGRES_TABLE,
    _CREATE_TABLE,
    _cache_db_path,
    doc_version_atual,
    get_chat_cache,
)
from src.rag.faq_catalog import FAQ_CATALOG, FAQItem  # noqa: E402
from src.storage.database import (  # noqa: E402
    database_url,
    postgres_connection,
    sqlite_connection,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("warmup_cache")


async def clear_cache_db() -> None:
    """Limpa a tabela de cache para um pré-aquecimento limpo."""
    if database_url():
        async with postgres_connection() as db:
            await db.execute(_CREATE_POSTGRES_TABLE)
            await db.execute("DELETE FROM chat_cache")
        logger.info("Tabela de cache PostgreSQL limpa com sucesso.")
    else:
        async with sqlite_connection(_cache_db_path()) as db:
            await db.execute(_CREATE_TABLE)
            await db.execute("DELETE FROM chat_cache")
            await db.commit()
        logger.info("Tabela de cache SQLite limpa com sucesso (%s).", _cache_db_path())


async def warmup_semantic_cache(
    catalog: list[FAQItem] | None = None,
    profile_filter: str = "all",
    clear_first: bool = False,
    dry_run: bool = False,
    limit: int | None = None,
) -> int:
    """Executa o pré-aquecimento do cache semântico com o catálogo de FAQs.

    Args:
        catalog: Lista de FAQs (padrão: FAQ_CATALOG).
        profile_filter: 'all', 'student' ou 'staff'.
        clear_first: Se True, limpa a tabela de cache antes de gravar.
        dry_run: Se True, apenas valida o catálogo sem gravar no banco.
        limit: Quantidade máxima de itens a processar.

    Returns:
        Total de itens aquecidos com sucesso.
    """
    items = catalog or FAQ_CATALOG
    if profile_filter in ("student", "staff"):
        items = [i for i in items if i["profile"] == profile_filter]

    if limit and limit > 0:
        items = items[:limit]

    logger.info(
        "Iniciando Semantic Cache Warmup: %d itens selecionados (Perfil: %s, Dry-run: %s)",
        len(items),
        profile_filter,
        dry_run,
    )

    if dry_run:
        for idx, item in enumerate(items, 1):
            logger.info(
                "  [%d/%d] [DRY-RUN] [%s] %s", idx, len(items), item["profile"], item["question"]
            )
        logger.info("Dry-run concluído com sucesso. Nenhum dado foi gravado.")
        return len(items)

    if clear_first:
        await clear_cache_db()

    cache = get_chat_cache()
    doc_version = doc_version_atual()
    logger.info("Versão do manifesto de documentos: '%s'", doc_version or "neutra")

    start_time = time.perf_counter()
    warmed_count = 0

    for idx, item in enumerate(items, 1):
        answer_payload = {
            "response": item["answer"],
            "intent": item["intent"],
            "sources": item["sources"],
            "agent": item["intent"],
            "plan": None,
        }
        success = await cache.store(
            profile=item["profile"],
            question=item["question"],
            answer=answer_payload,
            doc_version=doc_version,
        )
        if success:
            warmed_count += 1
            logger.info(
                "  [%d/%d] ✅ Gravado: [%s] '%s'",
                idx,
                len(items),
                item["profile"],
                item["question"],
            )
        else:
            logger.warning(
                "  [%d/%d] ⚠️ Falha ao gravar: [%s] '%s'",
                idx,
                len(items),
                item["profile"],
                item["question"],
            )

    elapsed = time.perf_counter() - start_time
    logger.info(
        "🚀 Semantic Cache Warmup Concluído: %d/%d itens cacheados em %.2fs (%.1f itens/s).",
        warmed_count,
        len(items),
        elapsed,
        warmed_count / elapsed if elapsed > 0 else 0,
    )
    return warmed_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pré-aquecimento do Semantic Cache do UsiEdu com FAQs canônicas.",
    )
    parser.add_argument(
        "--profile",
        choices=["all", "student", "staff"],
        default="all",
        help="Filtra os itens por perfil (padrão: all)",
    )
    parser.add_argument(
        "--clear-first",
        action="store_true",
        help="Limpa a tabela de cache antes de iniciar o aquecimento",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas valida o catálogo sem gravar no banco de dados",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limite de itens a pré-aquecer",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        count = asyncio.run(
            warmup_semantic_cache(
                profile_filter=args.profile,
                clear_first=args.clear_first,
                dry_run=args.dry_run,
                limit=args.limit,
            )
        )
        if count == 0 and not args.dry_run:
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Warmup cancelado pelo usuário.")
        sys.exit(130)


if __name__ == "__main__":
    main()
